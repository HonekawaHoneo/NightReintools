param(
    [ValidateRange(1024, 65535)]
    [int] $Port = 8443
)

$ErrorActionPreference = 'Stop'
try {
    [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
} catch {
    # The server can still run if the current console does not support UTF-8 output.
}

$script:RootCaSubject = 'CN=Nightreign Boss Tool LAN Root CA'

function Test-PrivateIPv4 {
    param(
        [Parameter(Mandatory)]
        [System.Net.IPAddress] $Address
    )

    if ($Address.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork) {
        return $false
    }

    $bytes = $Address.GetAddressBytes()
    return ($bytes[0] -eq 10) -or
        (($bytes[0] -eq 172) -and ($bytes[1] -ge 16) -and ($bytes[1] -le 31)) -or
        (($bytes[0] -eq 192) -and ($bytes[1] -eq 168))
}

function Get-LanIPv4 {
    $candidates = New-Object 'System.Collections.Generic.List[object]'
    $configurations = Get-NetIPConfiguration -ErrorAction Stop

    foreach ($configuration in $configurations) {
        $interfaceIndex = [int] $configuration.InterfaceIndex
        $adapter = Get-NetAdapter -InterfaceIndex $interfaceIndex -ErrorAction SilentlyContinue
        if ($null -eq $adapter -or $adapter.Status -ne 'Up') {
            continue
        }

        $routes = @(
            Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' -InterfaceIndex $interfaceIndex -ErrorAction SilentlyContinue |
                Sort-Object -Property RouteMetric
        )
        $routeMetric = 10000
        if ($routes.Count -gt 0) {
            $routeMetric = [int] $routes[0].RouteMetric
        }

        $ipInterfaces = @(
            Get-NetIPInterface -AddressFamily IPv4 -InterfaceIndex $interfaceIndex -ErrorAction SilentlyContinue
        )
        $interfaceMetric = 10000
        if ($ipInterfaces.Count -gt 0) {
            $interfaceMetric = [int] $ipInterfaces[0].InterfaceMetric
        }

        $addresses = @(
            Get-NetIPAddress -AddressFamily IPv4 -InterfaceIndex $interfaceIndex -ErrorAction SilentlyContinue |
                Where-Object { $_.AddressState -eq 'Preferred' -and -not $_.SkipAsSource }
        )

        foreach ($addressEntry in $addresses) {
            $address = [System.Net.IPAddress]::Parse([string] $addressEntry.IPAddress)
            if (-not (Test-PrivateIPv4 -Address $address)) {
                continue
            }

            $priority = $routeMetric + $interfaceMetric
            if ($null -eq $configuration.IPv4DefaultGateway) {
                $priority += 10000
            }
            if ($adapter.HardwareInterface -ne $true) {
                $priority += 50000
            }

            $candidates.Add([pscustomobject] @{
                IPv4Address = $address.ToString()
                InterfaceAlias = [string] $adapter.Name
                Priority = $priority
            })
        }
    }

    if ($candidates.Count -eq 0) {
        throw '利用可能なプライベートLAN IPv4アドレスが見つかりません。PCをWi-FiまたはLANに接続してから再実行してください。'
    }

    return $candidates | Sort-Object -Property Priority, InterfaceAlias, IPv4Address | Select-Object -First 1
}

function Get-OrCreateRootCertificate {
    $minimumExpiry = (Get-Date).AddDays(90)
    $storedCertificates = Get-ChildItem -Path 'Cert:\CurrentUser\My' -ErrorAction Stop

    foreach ($certificate in $storedCertificates) {
        if ($certificate.Subject -ne $script:RootCaSubject -or
            $certificate.Issuer -ne $script:RootCaSubject -or
            -not $certificate.HasPrivateKey -or
            $certificate.NotAfter -le $minimumExpiry) {
            continue
        }

        $basicConstraintsExtension = $certificate.Extensions |
            Where-Object { $_.Oid.Value -eq '2.5.29.19' } |
            Select-Object -First 1
        if ($null -eq $basicConstraintsExtension) {
            continue
        }

        $basicConstraints = [System.Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]::new(
            $basicConstraintsExtension,
            $basicConstraintsExtension.Critical
        )
        if ($basicConstraints.CertificateAuthority) {
            return $certificate
        }
    }

    $rootParameters = @{
        Type = 'Custom'
        Subject = $script:RootCaSubject
        FriendlyName = 'Nightreign Boss Tool LAN Root CA'
        KeyAlgorithm = 'RSA'
        KeyLength = 3072
        HashAlgorithm = 'SHA256'
        KeyUsageProperty = 'Sign'
        KeyUsage = @('CertSign', 'CRLSign')
        KeyExportPolicy = 'NonExportable'
        NotBefore = (Get-Date).AddMinutes(-5)
        NotAfter = (Get-Date).AddYears(10)
        CertStoreLocation = 'Cert:\CurrentUser\My'
        TextExtension = @('2.5.29.19={critical}{text}ca=true&pathlength=0')
    }

    return New-SelfSignedCertificate @rootParameters
}

function Get-OrCreateServerCertificate {
    param(
        [Parameter(Mandatory)]
        [string] $LanAddress,
        [Parameter(Mandatory)]
        [System.Security.Cryptography.X509Certificates.X509Certificate2] $RootCertificate
    )

    $rootMarker = $RootCertificate.Thumbprint.Substring(0, 12)
    $serverSubject = 'CN=Nightreign Boss Tool HTTPS {0} {1}' -f $LanAddress, $rootMarker
    $minimumExpiry = (Get-Date).AddDays(7)
    $storedCertificates = Get-ChildItem -Path 'Cert:\CurrentUser\My' -ErrorAction Stop

    foreach ($certificate in $storedCertificates) {
        if ($certificate.Subject -eq $serverSubject -and
            $certificate.Issuer -eq $RootCertificate.Subject -and
            $certificate.HasPrivateKey -and
            $certificate.NotAfter -gt $minimumExpiry) {
            return $certificate
        }
    }

    $serverParameters = @{
        Type = 'Custom'
        Subject = $serverSubject
        FriendlyName = 'Nightreign Boss Tool LAN HTTPS Server'
        Signer = $RootCertificate
        KeyAlgorithm = 'RSA'
        KeyLength = 2048
        HashAlgorithm = 'SHA256'
        KeyUsageProperty = @('Sign', 'Decrypt')
        KeyUsage = @('DigitalSignature', 'KeyEncipherment')
        KeyExportPolicy = 'NonExportable'
        NotBefore = (Get-Date).AddMinutes(-5)
        NotAfter = (Get-Date).AddDays(30)
        CertStoreLocation = 'Cert:\CurrentUser\My'
        TextExtension = @(
            '2.5.29.19={critical}{text}ca=false',
            ('2.5.29.17={text}IPAddress=' + $LanAddress),
            '2.5.29.37={text}1.3.6.1.5.5.7.3.1'
        )
    }

    return New-SelfSignedCertificate @serverParameters
}

try {
    $network = Get-LanIPv4
    $rootCertificate = Get-OrCreateRootCertificate
    $serverCertificate = Get-OrCreateServerCertificate -LanAddress $network.IPv4Address -RootCertificate $rootCertificate

    $certificateDirectory = Join-Path $PSScriptRoot 'certificates'
    if (-not (Test-Path -LiteralPath $certificateDirectory -PathType Container)) {
        New-Item -Path $certificateDirectory -ItemType Directory -Force | Out-Null
    }
    $rootCertificatePath = Join-Path $certificateDirectory 'nightreign-local-root-ca.cer'
    $publicCertificate = $rootCertificate.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert)
    [System.IO.File]::WriteAllBytes($rootCertificatePath, $publicCertificate)

    $url = 'https://{0}:{1}/' -f $network.IPv4Address, $Port
    Write-Host ''
    Write-Host '夜の王チェッカーを同一LAN内でHTTPS配信します。' -ForegroundColor Cyan
    Write-Host ('LANアドレス: {0} ({1})' -f $network.IPv4Address, $network.InterfaceAlias)
    Write-Host ('iPad用証明書: {0}' -f $rootCertificatePath)
    Write-Host ('iPadで開くURL: {0}' -f $url) -ForegroundColor Green
    Write-Host '先に証明書をiPadへ送り、インストールして全面的に信頼してください。'
    Write-Host '終了するには Ctrl+C を押してください。'
    Write-Host ''

    & (Join-Path $PSScriptRoot 'https-static-server.ps1') `
        -WebRoot $PSScriptRoot `
        -LanIPv4 $network.IPv4Address `
        -Port $Port `
        -CertificateThumbprint $serverCertificate.Thumbprint
} catch {
    Write-Host ''
    Write-Host ('起動できませんでした: {0}' -f $_.Exception.Message) -ForegroundColor Red
    exit 1
}
