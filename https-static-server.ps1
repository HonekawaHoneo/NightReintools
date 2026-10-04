param(
    [Parameter(Mandatory)]
    [string] $WebRoot,
    [Parameter(Mandatory)]
    [string] $LanIPv4,
    [ValidateRange(1024, 65535)]
    [int] $Port = 8443,
    [Parameter(Mandatory)]
    [string] $CertificateThumbprint
)

$ErrorActionPreference = 'Stop'

function Write-HttpResponse {
    param(
        [Parameter(Mandatory)]
        [System.IO.Stream] $Stream,
        [Parameter(Mandatory)]
        [int] $StatusCode,
        [Parameter(Mandatory)]
        [string] $Reason,
        [Parameter(Mandatory)]
        [string] $ContentType,
        [Parameter(Mandatory)]
        [byte[]] $Body,
        [switch] $HeadOnly
    )

    $header = "HTTP/1.1 $StatusCode $Reason`r`n" +
        "Content-Type: $ContentType`r`n" +
        "Content-Length: $($Body.Length)`r`n" +
        "Cache-Control: no-cache`r`n" +
        "X-Content-Type-Options: nosniff`r`n" +
        "Referrer-Policy: no-referrer`r`n" +
        "Connection: close`r`n`r`n"
    $headerBytes = [System.Text.Encoding]::ASCII.GetBytes($header)
    $Stream.Write($headerBytes, 0, $headerBytes.Length)
    if (-not $HeadOnly -and $Body.Length -gt 0) {
        $Stream.Write($Body, 0, $Body.Length)
    }
    $Stream.Flush()
}

function Read-HttpRequestLine {
    param(
        [Parameter(Mandatory)]
        [System.IO.Stream] $Stream
    )

    $maximumHeaderBytes = 16384
    $buffer = New-Object byte[] 2048
    $memory = New-Object System.IO.MemoryStream

    try {
        while ($memory.Length -lt $maximumHeaderBytes) {
            $count = $Stream.Read($buffer, 0, $buffer.Length)
            if ($count -le 0) {
                return $null
            }

            $memory.Write($buffer, 0, $count)
            $text = [System.Text.Encoding]::ASCII.GetString($memory.ToArray())
            if ($text.Contains("`r`n`r`n")) {
                $lineEnd = $text.IndexOf("`r`n", [System.StringComparison]::Ordinal)
                if ($lineEnd -lt 0) {
                    return $null
                }
                return $text.Substring(0, $lineEnd)
            }
        }

        return ''
    } finally {
        $memory.Dispose()
    }
}

function Get-AllowedStaticFile {
    param(
        [Parameter(Mandatory)]
        [string] $RequestPath,
        [Parameter(Mandatory)]
        [string] $RootPath
    )

    $allowedPaths = @(
        '/',
        '/index.html',
        '/manifest.webmanifest',
        '/service-worker.js',
        '/styles.css',
        '/resistance.css',
        '/mapping-data.js',
        '/resistance-data.js',
        '/app.js',
        '/assets/icon.svg',
        '/assets/icon-180.png',
        '/assets/icon-192.png',
        '/assets/icon-512.png'
    )

    if ($RequestPath -notin $allowedPaths) {
        return $null
    }

    $relativePath = if ($RequestPath -eq '/') { 'index.html' } else { $RequestPath.TrimStart('/') }
    $relativePath = $relativePath.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
    $rootFullPath = [System.IO.Path]::GetFullPath($RootPath).TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
    $fileFullPath = [System.IO.Path]::GetFullPath((Join-Path $rootFullPath $relativePath))
    if (-not $fileFullPath.StartsWith($rootFullPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $null
    }
    if (-not (Test-Path -LiteralPath $fileFullPath -PathType Leaf)) {
        return $null
    }

    return $fileFullPath
}

function Get-ContentType {
    param(
        [Parameter(Mandatory)]
        [string] $FilePath
    )

    switch ([System.IO.Path]::GetExtension($FilePath).ToLowerInvariant()) {
        '.html' { return 'text/html; charset=utf-8' }
        '.css' { return 'text/css; charset=utf-8' }
        '.js' { return 'application/javascript; charset=utf-8' }
        '.webmanifest' { return 'application/manifest+json; charset=utf-8' }
        '.svg' { return 'image/svg+xml' }
        '.png' { return 'image/png' }
        default { return 'application/octet-stream' }
    }
}

function Send-TextError {
    param(
        [Parameter(Mandatory)]
        [System.IO.Stream] $Stream,
        [Parameter(Mandatory)]
        [int] $StatusCode,
        [Parameter(Mandatory)]
        [string] $Reason,
        [Parameter(Mandatory)]
        [string] $Message,
        [switch] $HeadOnly
    )

    $body = [System.Text.Encoding]::UTF8.GetBytes($Message)
    Write-HttpResponse -Stream $Stream -StatusCode $StatusCode -Reason $Reason -ContentType 'text/plain; charset=utf-8' -Body $body -HeadOnly:$HeadOnly
}

$bindAddress = [System.Net.IPAddress]::Parse($LanIPv4)
$addressBytes = $bindAddress.GetAddressBytes()
$isPrivateAddress = ($addressBytes[0] -eq 10) -or
    (($addressBytes[0] -eq 172) -and ($addressBytes[1] -ge 16) -and ($addressBytes[1] -le 31)) -or
    (($addressBytes[0] -eq 192) -and ($addressBytes[1] -eq 168))
if ($bindAddress.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork -or -not $isPrivateAddress) {
    throw 'HTTPS配信先はプライベートLANのIPv4アドレスである必要があります。'
}

$thumbprint = ($CertificateThumbprint -replace '\s', '').ToUpperInvariant()
$certificate = Get-Item -LiteralPath ('Cert:\CurrentUser\My\{0}' -f $thumbprint) -ErrorAction Stop
if (-not $certificate.HasPrivateKey) {
    throw 'HTTPSサーバー証明書の秘密鍵が見つかりません。'
}

$webRootFullPath = [System.IO.Path]::GetFullPath($WebRoot)
$listener = [System.Net.Sockets.TcpListener]::new($bindAddress, $Port)

try {
    $listener.Start(32)
    Write-Host ('HTTPS配信中: https://{0}:{1}/' -f $LanIPv4, $Port) -ForegroundColor Green

    while ($true) {
        $client = $listener.AcceptTcpClient()
        $client.ReceiveTimeout = 15000
        $client.SendTimeout = 15000
        $sslStream = $null

        try {
            $sslStream = [System.Net.Security.SslStream]::new($client.GetStream(), $false)
            $sslStream.AuthenticateAsServer(
                $certificate,
                $false,
                [System.Security.Authentication.SslProtocols]::Tls12,
                $false
            )

            $requestLine = Read-HttpRequestLine -Stream $sslStream
            if ($null -eq $requestLine) {
                continue
            }
            if ($requestLine.Length -eq 0 -or $requestLine.Length -gt 2048) {
                Send-TextError -Stream $sslStream -StatusCode 431 -Reason 'Request Header Fields Too Large' -Message 'Request headers too large.'
                continue
            }

            $requestParts = $requestLine -split '\s+', 3
            if ($requestParts.Count -ne 3 -or $requestParts[2] -notmatch '^HTTP/1\.[01]$') {
                Send-TextError -Stream $sslStream -StatusCode 400 -Reason 'Bad Request' -Message 'Bad request.'
                continue
            }

            $method = $requestParts[0].ToUpperInvariant()
            $headOnly = $method -eq 'HEAD'
            if ($method -notin @('GET', 'HEAD')) {
                Send-TextError -Stream $sslStream -StatusCode 405 -Reason 'Method Not Allowed' -Message 'Only GET and HEAD are supported.'
                continue
            }

            $requestTarget = $requestParts[1]
            if (-not $requestTarget.StartsWith('/')) {
                Send-TextError -Stream $sslStream -StatusCode 400 -Reason 'Bad Request' -Message 'Bad request target.' -HeadOnly:$headOnly
                continue
            }
            $queryIndex = $requestTarget.IndexOf('?')
            if ($queryIndex -ge 0) {
                $requestTarget = $requestTarget.Substring(0, $queryIndex)
            }

            try {
                $requestPath = [System.Uri]::UnescapeDataString($requestTarget)
            } catch {
                Send-TextError -Stream $sslStream -StatusCode 400 -Reason 'Bad Request' -Message 'Invalid request path.' -HeadOnly:$headOnly
                continue
            }

            $filePath = Get-AllowedStaticFile -RequestPath $requestPath -RootPath $webRootFullPath
            if ($null -eq $filePath) {
                Send-TextError -Stream $sslStream -StatusCode 404 -Reason 'Not Found' -Message 'Not found.' -HeadOnly:$headOnly
                Write-Host ('{0} {1} -> 404' -f $method, $requestPath)
                continue
            }

            $body = [System.IO.File]::ReadAllBytes($filePath)
            Write-HttpResponse -Stream $sslStream -StatusCode 200 -Reason 'OK' -ContentType (Get-ContentType -FilePath $filePath) -Body $body -HeadOnly:$headOnly
            Write-Host ('{0} {1} -> 200' -f $method, $requestPath)
        } catch {
            Write-Host '接続を終了しました。' -ForegroundColor DarkYellow
        } finally {
            if ($null -ne $sslStream) {
                $sslStream.Dispose()
            }
            $client.Dispose()
        }
    }
} finally {
    $listener.Stop()
    $certificate.Dispose()
}
