"""Semantic UI rules with explicit workflow callbacks and no harness dependency."""
import fnmatch
from functools import lru_cache
import json
from pathlib import Path
import re
import uuid
from dataclasses import dataclass
from typing import Callable
import common as h
import ui_principles as principles

@dataclass(frozen=True)
class WorkflowHooks:
    artifact: Callable
    config: Callable
    exclusive: Callable
    integrity: Callable
    request_ids: Callable
    source_delta: Callable
    state: Callable
    validate_receipt: Callable

class UIContract:

    def __init__(self, workflow):
        self.workflow = workflow

    def objects(self, value, label, minimum=0):
        items = h.sequence(value, label, minimum)
        h.require(all((isinstance(item, dict) for item in items)), f'{label}: オブジェクトの配列が必要です')
        return items

    def settings(self, root, project):
        value = project.get('ui')
        if value is None:
            return None
        h.require(isinstance(value, dict) and type(value.get('schema_version')) is int and value.get('schema_version') in (1, 2, 3), 'ui.schema_versionは1/2/3です')
        h.require(value.get('mode') in ('observe', 'enforce'), 'ui.modeはobserve/enforceです')
        h.safe_path(root, value.get('registry'))
        for pattern in h.strings(value.get('input_globs'), 'ui.input_globs', 1):
            h.safe_path(root, pattern)
            h.require('{' not in pattern and '}' not in pattern, 'ui.input_globsはbrace展開に未対応です。拡張子ごとにglobを指定してください')
        ids = h.strings(value.get('check_ids'), 'ui.check_ids', 1)
        registered = {check['id'] for check in project['checks']}
        h.require(len(ids) == len(set(ids)) and set(ids) <= registered, 'ui.check_idsが未登録・重複しています')
        return value

    def policy_snapshot(self, project):
        policy = project.get('ui')
        if not policy or policy.get('schema_version') not in (2, 3):
            return None
        return {'ui': policy, 'checks': [check for check in project['checks'] if check['id'] in policy['check_ids']]}

    def strict_registry(self, root, value, policy, deferred=()):
        if policy['schema_version'] in (2, 3):
            principles.validate_registry(root, value, policy, self.matches, deferred)
        return value

    def reference(self, root, ref, label, deferred=()):
        h.require(isinstance(ref, dict), f'{label}: source_refが必要です')
        relative = h.nonempty(ref.get('path'), f'{label}.path')
        path = h.safe_path(root, relative)
        if not path.is_file():
            h.require(relative in deferred, f'{label}: 定義元がありません: {relative}')
            return None
        pointer = ref.get('pointer')
        if pointer is None:
            return None
        h.require(isinstance(pointer, str) and (pointer == '' or pointer.startswith('/')), f'{label}: 不正なJSON pointer')
        try:
            value = json.loads(path.read_text(encoding='utf-8'))
        except (ValueError, UnicodeError) as exc:
            raise h.GateError(f'{label}: JSON定義元を読めません: {relative}') from exc
        if pointer:
            for part in pointer[1:].split('/'):
                h.require(not re.search('~(?![01])', part), f'{label}: 不正なJSON pointer')
                part = part.replace('~1', '/').replace('~0', '~')
                try:
                    if isinstance(value, list):
                        h.require(bool(re.fullmatch('0|[1-9][0-9]*', part)), f'{label}: 不正な配列pointer')
                        value = value[int(part)]
                    else:
                        h.require(isinstance(value, dict), f'{label}: pointerがオブジェクトを指していません')
                        value = value[part]
                except (KeyError, IndexError) as exc:
                    if relative in deferred:
                        return None
                    raise h.GateError(f'{label}: JSON pointerがありません: {pointer}') from exc
        return value

    def registry_sources(self, value):
        return {entry[key]['path'] for group in ('components', 'tokens') for entry in value[group] for key in ('source_ref', 'variants_ref', 'states_ref') if key in entry} | {ref['path'] for ref in value.get('sources', [])}

    def empty_registry(self, value):
        return isinstance(value, dict) and value.get('schema_version') == 1 and all(
            value.get(group) == [] for group in ('sources', 'components', 'tokens'))

    def validate_registry(self, root, value, deferred=(), allow_empty=False):
        h.require(isinstance(value, dict) and value.get('schema_version') == 1, 'Registry schema_versionは1です')
        for ref in self.objects(value.get('sources', []), 'registry.sources'):
            self.reference(root, ref, 'registry.sources', deferred)
        groups = {}
        for group in ('components', 'tokens'):
            ids = set()
            entries = h.sequence(value.get(group), f'registry.{group}', int(group == 'components' and not allow_empty))
            for entry in entries:
                h.require(isinstance(entry, dict), f'registry.{group}: オブジェクトが必要です')
                name = h.nonempty(entry.get('id'), f'{group}.id')
                h.require(name not in ids, f'Registry IDが重複しています: {name}')
                ids.add(name)
                h.nonempty(entry.get('meaning'), f'{name}.meaning')
                self.reference(root, entry.get('source_ref'), name, deferred)
                if group == 'components':
                    for key in ('use_when', 'token_ids', 'required_cues', 'optional_cues', 'avoid', 'a11y'):
                        h.strings(entry.get(key), f'{name}.{key}', int(key == 'use_when'))
                    for relation in self.objects(entry.get('relations'), f'{name}.relations'):
                        h.nonempty(relation.get('kind'), 'relation.kind')
                        h.nonempty(relation.get('component'), 'relation.component')
                    for key in ('variants_ref', 'states_ref'):
                        if key in entry:
                            options = self.reference(root, entry[key], f'{name}.{key}', deferred)
                            if options is not None:
                                h.strings(options, f'{name}.{key}', 1)
                                h.require(len(options) == len(set(options)), f'{name}.{key}: 重複した選択肢')
            groups[group] = ids
        for entry in value['components']:
            h.require(set(entry['token_ids']) <= groups['tokens'], f"{entry['id']}: 不明なtoken参照")
            h.require(all((relation['component'] in groups['components'] for relation in entry['relations'])), f"{entry['id']}: 不明なcomponent relation参照")
        return value

    def file_ref(self, root, path):
        target = h.safe_path(root, path)
        h.require(target.is_file(), f'添付ファイルがありません: {path}')
        return {'path': path, 'sha256': h.file_sha(target)}

    def verify_ref(self, root, ref, label):
        h.require(isinstance(ref, dict), f'{label}: pathとsha256が必要です')
        actual = self.file_ref(root, ref.get('path'))
        h.require(actual['sha256'] == ref.get('sha256'), f'{label}: 指紋が変わっています')
        return h.safe_path(root, actual['path'])

    def environment(self, value):
        h.require(isinstance(value, dict), 'capture.environmentが必要です')
        viewport = value.get('viewport')
        h.require(isinstance(viewport, dict) and all((type(viewport.get(k)) is int and viewport[k] > 0 for k in ('width', 'height'))), 'viewportには正のwidth/heightが必要です')
        for key in ('browser', 'theme', 'fixture'):
            h.nonempty(value.get(key), f'environment.{key}')
        return value

    def screenshot(self, root, relative):
        ref = self.file_ref(root, relative)
        data = h.safe_path(root, relative).read_bytes()
        h.require(data.startswith(b'\x89PNG\r\n\x1a\n') or data.startswith(b'\xff\xd8\xff') or (data.startswith(b'RIFF') and data[8:12] == b'WEBP'), f'screenshot形式ではありません: {relative}')
        return ref

    def prepare(self, root, identifier, candidate=None, approval_ref=None, approved_sources=(), before=()):
        self.workflow.integrity(root)
        current = self.workflow.state(root, identifier)
        h.require(current['phase'] in ('discovery', 'requirements', 'design'), 'prepareはUIソースの実装前に実行します')
        project = self.workflow.config(root)
        policy = self.settings(root, project)
        h.require(policy is not None, 'ui設定がありません')
        baseline = h.read_json(h.safe_path(root, policy['registry']))
        bootstrap = policy['schema_version'] in (2, 3) and current['kind'] == 'new' and self.empty_registry(baseline) and candidate is not None
        self.validate_registry(root, baseline, allow_empty=bootstrap)
        if not bootstrap:
            self.strict_registry(root, baseline, policy)
        changed = self.workflow.source_delta(root, current)
        sources = self.registry_sources(baseline) | {policy['registry']}
        h.require(not any((self.matches(path, pattern) for path in changed for pattern in policy['input_globs'])) and (not set(changed) & sources), 'before snapshotはUIソースの変更前に取得してください')
        approvals = list(approved_sources)
        for path in approvals:
            h.safe_path(root, path)
            h.require(path in sources, f'承認対象が既存の定義元ではありません: {path}')
        planned = h.read_json(h.safe_path(root, candidate)) if candidate is not None else baseline
        if candidate is not None or approvals:
            h.nonempty(approval_ref, 'approval_ref: 実際の承認参照')
        new_sources = self.registry_sources(planned) - sources if candidate is not None else set()
        if candidate is not None and policy['schema_version'] in (2, 3):
            new_sources |= {c['implementation_ref']['path'] for c in planned.get('components', [])
                            if isinstance(c, dict) and isinstance(c.get('implementation_ref'), dict)
                            and isinstance(c['implementation_ref'].get('path'), str)
                            and not h.safe_path(root, c['implementation_ref']['path']).is_file()}
        if candidate is not None:
            approvals.extend([policy['registry'], *sorted(new_sources)])
        self.validate_registry(root, planned, approvals)
        self.strict_registry(root, planned, policy, approvals)
        captures = []
        seen = set()
        evidence_prefix = f'.harness/changes/{identifier}/evidence/'
        for entry in self.objects(list(before), 'before'):
            name = h.nonempty(entry.get('scenario'), 'before.scenario')
            h.require(name not in seen, 'before.scenarioが重複しています')
            seen.add(name)
            path = h.nonempty(entry.get('path'), 'before.path')
            h.require(path.startswith(evidence_prefix), 'before画像は対象変更のevidence内に置いてください')
            captures.append({'scenario': name, **self.screenshot(root, path), 'environment': self.environment(entry.get('environment'))})
        snapshot = {'schema_version': 1, 'registry_path': policy['registry'], 'registry': planned, 'baseline_registry': baseline, 'source_digests': {p: h.file_sha(h.safe_path(root, p)) for p in sorted(sources)}, 'approved_sources': sorted(set(approvals)), 'approval_ref': approval_ref, 'before': captures}
        if policy['schema_version'] in (2, 3):
            snapshot['bootstrap'] = bootstrap
            inputs = root / f'.harness/changes/{identifier}/inputs'
            snapshot['input_digests'] = {p.relative_to(root).as_posix(): h.file_sha(h.safe_path(root, p.relative_to(root).as_posix()))
                                         for p in sorted(inputs.rglob('*')) if p.is_file()}
        if policy['schema_version'] == 3:
            implementation_paths = {
                h.safe_path(root, c['implementation_ref']['path']).resolve().relative_to(root.resolve()).as_posix()
                for c in planned['components']}
            # Registry may name only the non-UI target of a captured UI symlink.
            for source in sources | set(current['baseline_files']):
                target = h.safe_path(root, source)
                canonical = target.resolve().relative_to(root.resolve()).as_posix()
                if any(self.matches(candidate, pattern)
                       for candidate in (target.relative_to(root).as_posix(), canonical)
                       for pattern in policy['input_globs']):
                    implementation_paths.add(canonical)
            snapshot['implementation_paths'] = sorted(implementation_paths)
            requirements = f'.harness/changes/{identifier}/requirements.json'
            path = h.safe_path(root, requirements)
            snapshot['requirements_digests'] = {requirements: h.file_sha(path)} if path.is_file() else {}
        relative = f'.harness/changes/{identifier}/inputs/ui-{uuid.uuid4().hex}.json'
        h.write_json(h.safe_path(root, relative), snapshot)
        return self.file_ref(root, relative)

    def matches(self, path, pattern, directory=False):
        parts = tuple(Path(path).parts)
        patterns = tuple(pattern.rstrip('/').split('/'))

        @lru_cache(maxsize=None)
        def visit(part, pattern_part):
            if pattern_part == len(patterns):
                return part == len(parts)
            if directory and part == len(parts):
                return True
            if patterns[pattern_part] == '**':
                return visit(part, pattern_part + 1) or (part < len(parts) and visit(part + 1, pattern_part))
            return part < len(parts) and fnmatch.fnmatchcase(parts[part], patterns[pattern_part]) and visit(part + 1, pattern_part + 1)
        prefix = re.split('[*?\\[]', pattern, maxsplit=1)[0].rstrip('/')
        return visit(0, 0) or bool(prefix and (prefix == path or prefix.startswith(path.rstrip('/') + '/')))

    def design_ui(self, root, identifier):
        return self.workflow.artifact(root, identifier, 'design').get('ui')

    def read_snapshot(self, root, identifier, design):
        ref = design.get('registry_snapshot')
        path = self.verify_ref(root, ref, 'registry snapshot')
        h.require(ref['path'].startswith(f'.harness/changes/{identifier}/inputs/'), 'snapshotは対象変更のinputs内に置いてください')
        value = h.read_json(path)
        h.require(value.get('schema_version') == 1, '不正なregistry snapshot')
        h.require(value.get('registry_path') == self.workflow.config(root)['ui']['registry'], 'Registry接続がsnapshotと異なります')
        h.require(isinstance(value.get('source_digests'), dict) and value['source_digests'], 'snapshotの定義元がありません')
        if self.workflow.config(root)['ui']['schema_version'] in (2, 3):
            digests = value.get('input_digests')
            h.require(isinstance(digests, dict), 'v2 snapshot.input_digestsが必要です')
            for relative, expected in digests.items():
                h.require(isinstance(relative, str) and relative.startswith(f'.harness/changes/{identifier}/inputs/'),
                          'snapshot inputは対象変更のinputs内に置いてください')
                path = h.safe_path(root, relative)
                h.require(path.is_file() and h.file_sha(path) == expected, '実装前のUI inputの指紋が変わっています')
            for principle in self.objects(design.get('principles'), 'ui.principles', 1):
                if principle.get('id') == 'structure':
                    details = principle.get('details')
                    h.require(isinstance(details, dict) and isinstance(details.get('wireframe_ref'), dict) and
                              isinstance(details['wireframe_ref'].get('path'), str) and
                              details['wireframe_ref']['path'] in digests, 'wireframeはprepare前にinputsへ保存してください')
        approvals = h.strings(value.get('approved_sources'), 'snapshot.approved_sources')
        if approvals:
            h.nonempty(value.get('approval_ref'), 'snapshot.approval_ref')
        self.validate_registry(root, value.get('registry'), set(value['source_digests']) | set(approvals))
        for capture in h.sequence(value.get('before'), 'snapshot.before'):
            self.verify_ref(root, capture, 'before screenshot')
            self.environment(capture.get('environment'))
        return value

    def validate_design(self, root, identifier, item, current):
        policy = self.workflow.config(root).get('ui')
        if policy is None:
            return
        paths = item['impact_paths'] + self.workflow.source_delta(root, current)
        registry = h.read_json(h.safe_path(root, policy['registry']))
        bootstrap = policy['schema_version'] in (2, 3) and current['kind'] == 'new' and self.empty_registry(registry)
        self.validate_registry(root, registry, allow_empty=bootstrap)
        if not bootstrap:
            self.strict_registry(root, registry, policy)
        if policy['schema_version'] in (2, 3):
            h.require(current.get('ui_policy') is not None, 'v2 UI policyはnewから固定してください')
        sources = self.registry_sources(registry) | {policy['registry']}
        affected = any((self.matches(path, pattern, (root / path).is_dir()) for path in paths for pattern in policy['input_globs'])) or any((path == source or source.startswith(path.rstrip('/') + '/') for path in paths for source in sources))
        design = item.get('ui')
        if design is None:
            h.require(not affected or policy['mode'] == 'observe', 'UI変更にはdesign.uiが必要です')
            return
        h.require(isinstance(design, dict) and design.get('scope') in ('none', 'local', 'shared'), 'UI scopeが不正です')
        h.nonempty(design.get('reason'), 'ui.reason')
        if design['scope'] == 'none':
            h.require(not affected, 'UI変更をscope=noneにはできません')
            return
        shared = any((path == source or source.startswith(path.rstrip('/') + '/') for path in paths for source in sources))
        h.require(not shared or design['scope'] == 'shared', '共有デザイン定義の変更はscope=sharedで検証してください')
        snapshot = self.read_snapshot(root, identifier, design)
        if bootstrap:
            h.require(snapshot.get('bootstrap') is True and snapshot.get('baseline_registry') == registry,
                      '空のUI baselineには承認済みbootstrap candidateが必要です')
            h.nonempty(snapshot.get('approval_ref'), 'bootstrap approval_ref')
        components = {entry['id']: entry for entry in snapshot['registry']['components']}
        token_ids = {entry['id'] for entry in snapshot['registry']['tokens']}
        meanings = set()
        for entry in self.objects(design.get('meanings'), 'ui.meanings', 1):
            name = h.nonempty(entry.get('id'), 'meaning.id')
            h.require(name not in meanings, 'meaning IDが重複しています')
            meanings.add(name)
            h.require(entry.get('requirement') in self.workflow.request_ids(root, identifier), 'meaningの要件参照が不正です')
            h.nonempty(entry.get('meaning'), 'meaning.meaning')
        covered = set()
        for entry in self.objects(design.get('decisions'), 'ui.decisions', 1):
            name = entry.get('meaning')
            h.require(name in meanings and name not in covered, 'decisionのmeaning参照が不正・重複しています')
            covered.add(name)
            h.require(entry.get('component') in components, '不明なcomponent参照')
            component = components[entry['component']]
            h.strings(entry.get('cues'), 'decision.cues', 1)
            for omitted in self.objects(entry.get('omitted'), 'decision.omitted'):
                h.nonempty(omitted.get('cue'), 'omitted.cue')
                h.nonempty(omitted.get('reason'), 'omitted.reason')
            selected = h.strings(entry.get('tokens'), 'decision.tokens')
            h.require(set(selected) <= token_ids and set(selected) <= set(component['token_ids']), '不明・用途外のtoken参照')
            for key, options_ref in (('variant', 'variants_ref'), ('state', 'states_ref')):
                if key in entry:
                    h.nonempty(entry[key], f'decision.{key}')
                    if options_ref in component:
                        options = self.reference(root, component[options_ref], options_ref, snapshot['approved_sources'])
                        pending = component[options_ref]['path'] in snapshot['approved_sources']
                        h.require(pending or options is None or entry[key] in options, f'不明な{key}参照')
        h.require(covered == meanings, '全meaningにdecisionが必要です')
        for component_id in {entry['component'] for entry in design['decisions']}:
            cues = {cue for entry in design['decisions'] if entry['component'] == component_id for cue in entry['cues']}
            h.require(set(components[component_id]['required_cues']) <= cues, f'{component_id}: 必須cueの表現が不足しています')
        covered = set()
        scenario_ids = set()
        captures = {entry['scenario'] for entry in snapshot['before']}
        for entry in self.objects(design.get('scenarios'), 'ui.scenarios', 1):
            name = h.nonempty(entry.get('id'), 'scenario.id')
            h.require(name not in scenario_ids, 'scenario IDが重複しています')
            scenario_ids.add(name)
            selected = h.strings(entry.get('meanings'), 'scenario.meanings', 1)
            h.require(set(selected) <= meanings, 'scenarioのmeaning参照が不正です')
            covered.update(selected)
            h.require(entry.get('check') in policy['check_ids'], 'scenarioのcheckがUI検証に登録されていません')
            h.nonempty(entry.get('preview'), 'scenario.preview')
            h.nonempty(entry.get('reason'), 'scenario.reason')
            h.require(entry.get('baseline') in ('existing', 'new'), 'scenario.baselineはexisting/newです')
            if entry['baseline'] == 'existing' and policy['mode'] == 'enforce':
                h.require(name in captures, f'existing scenarioのbefore画像がありません: {name}')
        h.require(covered == meanings, '全meaningにscenarioが必要です')
        if policy['schema_version'] in (2, 3):
            self.strict_registry(root, snapshot['registry'], policy, snapshot['approved_sources'])
            principles.validate_design(root, identifier, design, snapshot['registry'],
                                       self.workflow.request_ids(root, identifier), snapshot['approved_sources'],
                                       schema_version=policy['schema_version'], snapshot=snapshot)

    def validate_current(self, root, identifier):
        design = self.design_ui(root, identifier)
        if not design or design['scope'] == 'none':
            return None
        snapshot = self.read_snapshot(root, identifier, design)
        policy = self.workflow.config(root)['ui']
        current = self.validate_registry(root, h.read_json(h.safe_path(root, policy['registry'])))
        self.strict_registry(root, current, policy)
        if policy['schema_version'] in (2, 3):
            principles.validate_design(root, identifier, design, current, self.workflow.request_ids(root, identifier),
                                       schema_version=policy['schema_version'], snapshot=snapshot)
        h.require(current == snapshot['registry'], 'Registryが承認済みの予定と異なります')
        sources = self.registry_sources(current) | {policy['registry']}
        for path, before in snapshot['source_digests'].items():
            target = h.safe_path(root, path)
            if target.is_file():
                h.require(h.file_sha(target) == before or path in snapshot['approved_sources'], f'定義元に未承認の変更があります: {path}')
            else:
                h.require(not target.exists() and (not target.is_symlink()) and (path not in sources) and (path in snapshot['approved_sources']), f'定義元の削除が未承認または参照中です: {path}')
        for entry in design['decisions']:
            component = next((c for c in current['components'] if c['id'] == entry['component']))
            for key, option in (('variant', 'variants_ref'), ('state', 'states_ref')):
                if key in entry and option in component:
                    options = self.reference(root, component[option], option)
                    h.require(options is None or entry[key] in options, f'実装後の{key}参照が不正です')
        if policy['schema_version'] in (2, 3):
            sources |= {c['implementation_ref']['path'] for c in current['components']}
        return h.digest({'registry': current, 'sources': {p: h.file_sha(h.safe_path(root, p)) for p in sorted(sources)}})

    def validate_phase(self, root, identifier, phase, current, item, portable=False):
        if phase == 'design':
            self.validate_design(root, identifier, item, current)
        elif phase == 'review':
            self.validate_review(root, identifier, item, portable=portable)

    def collect(self, root, identifier, receipt, directory):
        policy = self.workflow.config(root).get('ui')
        if policy is None:
            return None
        design = self.design_ui(root, identifier)
        if design and design['scope'] == 'none':
            return None
        relative = directory.relative_to(root).as_posix()
        h.require(relative.startswith(f'.harness/changes/{identifier}/evidence/'), 'UI証跡の保存先が不正です')
        result = {'status': 'not_verified', 'directory': relative, 'registry_digest': None, 'reports': [], 'scenarios': [], 'issues': []}
        if not design:
            result['issues'].append('design.uiがなく意味と画面を照合できません')
            return result
        result['registry_digest'] = self.validate_current(root, identifier)
        snapshot = self.read_snapshot(root, identifier, design)
        before = {entry['scenario']: entry for entry in snapshot['before']}
        expected = {entry['id']: entry for entry in design['scenarios']}
        seen = set()
        for check_id in sorted({entry['check'] for entry in expected.values()}):
            provider_directory = directory / check_id
            path = provider_directory / f'{check_id}.ui.json'
            if not path.is_file():
                result['issues'].append(f'UI providerの報告がありません: {check_id}')
                continue
            report = h.read_json(path)
            result['reports'].append(self.file_ref(root, path.relative_to(root).as_posix()))
            h.require(type(report.get('schema_version')) is int and report.get('schema_version') == policy['schema_version'], 'UI provider schema_versionが設定と異なります')
            for entry in h.sequence(report.get('scenarios'), 'provider.scenarios'):
                h.require(isinstance(entry, dict), 'provider scenarioはオブジェクトです')
                name = entry.get('id')
                h.require(name in expected and name not in seen and (expected[name]['check'] == check_id), 'UI providerのscenarioが不明・重複・検証ID不一致です')
                seen.add(name)
                status = entry.get('status')
                h.require(status in ('passed', 'failed', 'not_verified'), 'UI provider statusが不正です')
                observation = h.nonempty(entry.get('observations'), 'provider.observations')
                env = self.environment(entry.get('environment'))
                files = []
                has_screenshot = False
                for attachment in h.sequence(entry.get('files'), 'provider.files'):
                    h.require(isinstance(attachment, dict), 'provider.filesはオブジェクトの配列です')
                    kind = attachment.get('kind')
                    h.require(kind in ('screenshot', 'aria', 'trace', 'metrics'), '添付kindが不正です')
                    target = h.safe_path(provider_directory, attachment.get('path'))
                    file_path = target.relative_to(root).as_posix()
                    ref = self.screenshot(root, file_path) if kind == 'screenshot' else self.file_ref(root, file_path)
                    files.append({**ref, 'kind': kind})
                    has_screenshot |= kind == 'screenshot'
                if not has_screenshot:
                    status = 'not_verified' if status != 'failed' else status
                    result['issues'].append(f'screenshotがありません: {name}')
                if expected[name]['baseline'] == 'existing':
                    if name not in before or before[name]['environment'] != env:
                        status = 'not_verified' if status != 'failed' else status
                        result['issues'].append(f'before画像または比較条件が一致しません: {name}')
                case_results = {}
                if policy['schema_version'] in (2, 3):
                    measured = principles.collect_cases(root, provider_directory, entry, design, files, snapshot['registry'])
                    case_results = {'case_results': measured}
                    if any(case['status'] == 'failed' for case in measured):
                        status = 'failed'
                result['scenarios'].append({'id': name, 'status': status, 'observations': observation, 'environment': env, 'files': files, **case_results})
        if seen != set(expected):
            result['issues'].append('必要なUI scenarioが未実行です')
        statuses = {entry['status'] for entry in result['scenarios']}
        if 'failed' in statuses:
            result['status'] = 'failed'
        elif seen == set(expected) and (not result['issues']) and (statuses == {'passed'}):
            result['status'] = 'passed'
        return result

    def validate_receipt(self, root, identifier, receipt):
        policy = self.workflow.config(root).get('ui')
        if policy is None:
            return
        design = self.design_ui(root, identifier)
        if design and design['scope'] == 'none':
            return
        recorded = receipt.get('ui')
        h.require(isinstance(recorded, dict), 'UI検証証跡がありません')
        directory = h.safe_path(root, recorded.get('directory'))
        actual = self.collect(root, identifier, receipt, directory)
        h.require(actual == recorded, 'UI報告・添付の指紋またはRegistryが変わっています')
        if policy['mode'] == 'enforce':
            h.require(recorded['status'] == 'passed', 'UI検証はpassedではありません')

    def validate_review(self, root, identifier, item, portable=False):
        policy = self.workflow.config(root).get('ui')
        design = self.design_ui(root, identifier)
        if policy is None or (design and design['scope'] == 'none'):
            return
        review = item.get('ui')
        if review is None and policy['mode'] == 'observe':
            h.require(bool(item['limitations']), 'UI未確認をreview.limitationsへ記録してください')
            return
        h.require(isinstance(review, dict), '独立したUI視覚レビューが必要です')
        h.require(review.get('status') in ('passed', 'request_changes', 'not_verified'), 'UI review.statusが不正です')
        if policy['mode'] == 'enforce':
            h.require(review['status'] == 'passed', 'UI視覚レビューはpassedではありません')
        if review['status'] != 'passed':
            h.require(bool(item['limitations']), 'UI未確認・指摘をreview.limitationsへ記録してください')
            return
        h.require(bool(design), 'design.uiなしでUI合格を主張できません')
        ref = review.get('receipt_ref')
        path = self.verify_ref(root, ref, 'reviewed UI receipt')
        h.require(ref['path'].startswith(f'.harness/changes/{identifier}/evidence/') and path.name != 'latest.json', 'UIレビューは対象変更の不変なreceiptを参照してください')
        reviewed = h.read_json(path)
        self.workflow.validate_receipt(root, identifier, portable=portable, receipt=reviewed)
        h.require(reviewed.get('ui', {}).get('status') == 'passed', '未確認・失敗したUI証跡を合格にできません')
        expected = {entry['id']: set(entry['meanings']) for entry in design['scenarios']}
        checked = h.strings(review.get('checked_scenarios'), 'review.ui.checked_scenarios', 1)
        h.require(len(checked) == len(set(checked)) and set(checked) == set(expected), 'UIレビューのscenario確認が不足しています')
        seen = set()
        for observation in self.objects(review.get('observations'), 'review.ui.observations', 1):
            name = observation.get('scenario')
            h.require(name in expected and name not in seen, 'UI観測のscenarioが不明・重複しています')
            seen.add(name)
            understood = h.strings(observation.get('understood'), 'review.ui.understood')
            h.require(set(understood) == expected[name], '必要なmeaningの識別結果が不足しています')
            h.require(h.strings(observation.get('excess'), 'review.ui.excess') == [] and h.strings(observation.get('missing'), 'review.ui.missing') == [], '未解決の過剰・不足表現があります')
            h.nonempty(observation.get('assessment'), 'review.ui.assessment')
        h.require(seen == set(expected), '全scenarioにUI観測が必要です')
        if policy['schema_version'] in (2, 3):
            principles.validate_review(review, design, reviewed['ui'], schema_version=policy['schema_version'])
