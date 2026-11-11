"""V2/V3 principle decisions, typed expectations and evidence-derived observations."""
import json
import math
import re
import common as h

PRINCIPLES = frozenset(('meaning', 'structure', 'reuse', 'visual_hierarchy', 'tokens',
    'density_typography', 'copy', 'states_actions', 'accessibility', 'scope_connections'))
OUTCOMES = frozenset(('success', 'failure', 'cancel', 'duplicate', 'late_response', 'focus'))
DIMENSIONS = frozenset(('font_size', 'line_height', 'row_height', 'target_size', 'spacing'))
ASPECTS = frozenset(('label', 'keyboard', 'focus', 'width', 'zoom', 'reading_order', 'operable_targets'))


def objects(value, label, minimum=1):
    result = h.sequence(value, label, minimum)
    h.require(all(isinstance(item, dict) for item in result), f'{label}: objectsが必要です')
    return result


def unique(value, label, minimum=0):
    values = h.strings(value, label, minimum)
    h.require(len(values) == len(set(values)), f'{label}: 重複しています')
    return set(values)


def json_value(value, label):
    h.require(value is None or type(value) in (str, bool, int, float, list, dict), f'{label}: JSON値が必要です')
    if type(value) is float:
        h.require(math.isfinite(value), f'{label}: 有限数が必要です')
    elif isinstance(value, list):
        for item in value:
            json_value(item, label)
    elif isinstance(value, dict):
        h.require(all(isinstance(key, str) for key in value), f'{label}: JSONキーは文字列です')
        for item in value.values():
            json_value(item, label)
    return value


def pointer_value(value, pointer, label):
    h.require(isinstance(pointer, str) and (pointer == '' or pointer.startswith('/')), f'{label}: 不正なJSON pointer')
    for part in pointer[1:].split('/') if pointer else []:
        h.require(not re.search(r'~(?![01])', part), f'{label}: 不正なJSON pointer')
        part = part.replace('~1', '/').replace('~0', '~')
        try:
            if isinstance(value, list):
                h.require(bool(re.fullmatch(r'0|[1-9][0-9]*', part)), f'{label}: 不正な配列pointer')
                value = value[int(part)]
            else:
                h.require(isinstance(value, dict), f'{label}: pointerがオブジェクトを指していません')
                value = value[part]
        except (KeyError, IndexError, ValueError) as exc:
            raise h.GateError(f'{label}: JSON pointerがありません: {pointer}') from exc
    return json_value(value, label)


def reference(root, ref, label, deferred=(), anchor_only=False):
    h.require(isinstance(ref, dict), f'{label}: source_refが必要です')
    path = h.safe_path(root, ref.get('path'))
    has_anchor, has_pointer = 'anchor' in ref, 'pointer' in ref
    h.require(has_anchor != has_pointer and (not anchor_only or has_anchor), f'{label}: 非空anchorまたはpointerが必要です')
    if has_anchor:
        h.nonempty(ref['anchor'], f'{label}.anchor')
    else:
        pointer = ref['pointer']
        h.require(isinstance(pointer, str) and (pointer == '' or pointer.startswith('/')) and
                  not re.search(r'~(?![01])', pointer), f'{label}: 不正なJSON pointer')
    if not path.is_file():
        h.require(ref['path'] in deferred, f'{label}: 定義元がありません: {ref["path"]}')
        return None
    try:
        text = path.read_text(encoding='utf-8')
        h.nonempty(text, f'{label}: 定義元')
        if has_anchor:
            if ref['anchor'] not in text and ref['path'] in deferred:
                return None
            h.require(ref['anchor'] in text, f'{label}: anchorがありません')
            return ref['anchor']
        value = pointer_value(json.loads(text), ref['pointer'], label)
    except (UnicodeError, ValueError) as exc:
        raise h.GateError(f'{label}: 定義元JSONを読めません') from exc
    except h.GateError as exc:
        if ref['path'] in deferred and 'JSON pointerがありません' in str(exc):
            return None
        raise
    h.require(value is not None and value != '' and value != [] and value != {}, f'{label}: 空の定義は使えません')
    return value


def expectation(value, label):
    h.require(isinstance(value, dict), f'{label}: expectationが必要です')
    operator = value.get('operator')
    if operator == 'equals':
        h.require('value' in value, f'{label}: valueが必要です')
        json_value(value['value'], label)
    else:
        h.require(operator == 'range', f'{label}: operatorはequals/rangeです')
        for key in ('min', 'max'):
            h.require(type(value.get(key)) in (int, float), f'{label}.{key}: 数値が必要です')
            json_value(value[key], label)
        h.require(value['min'] <= value['max'], f'{label}: minがmaxを超えています')
    return value


def equal(left, right):
    if type(left) in (int, float) and type(right) in (int, float):
        return left == right
    if type(left) is not type(right):
        return False
    if isinstance(left, list):
        return len(left) == len(right) and all(equal(a, b) for a, b in zip(left, right))
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(equal(left[k], right[k]) for k in left)
    return left == right


def matches(actual, expected):
    json_value(actual, 'actual')
    if expected['operator'] == 'equals':
        return equal(actual, expected['value'])
    return type(actual) in (int, float) and expected['min'] <= actual <= expected['max']


def validate_registry(root, registry, policy, path_matches, deferred=()):
    h.sequence(registry['tokens'], 'v2 registry.tokens', 1)
    for group in ('components', 'tokens'):
        for entry in registry[group]:
            value = reference(root, entry.get('source_ref'), entry['id']+'.source_ref', deferred)
            if group == 'tokens':
                h.require('pointer' in entry['source_ref'], 'token source_refは具体scalarを指すJSON pointerが必要です')
                h.require(value is None or type(value) in (str, int, float, bool), 'tokenは非空scalar具体値が必要です')
            if group == 'components':
                ref = entry.get('implementation_ref')
                reference(root, ref, entry['id']+'.implementation_ref', deferred, anchor_only=True)
                h.require(any(path_matches(ref['path'], pattern) for pattern in policy['input_globs']),
                          'implementation_refはUI input_globsに含めてください')
                h.strings(entry['token_ids'], entry['id']+'.token_ids', 1)
    for ref in registry.get('sources', []):
        reference(root, ref, 'registry.sources', deferred)


def validate_design(root, identifier, design, registry, request_ids, deferred=(), *, schema_version=2, snapshot=None):
    cases = {}
    scenarios = {s['id'] for s in design['scenarios']}
    tokens = {t['id']: reference(root, t['source_ref'], 'token '+t['id'], deferred) for t in registry['tokens']}
    for decision in design['decisions']:
        h.strings(decision.get('tokens'), 'v2 decision.tokens', 1)
    selected_tokens = {t for d in design['decisions'] for t in d['tokens']}
    h.require(bool(selected_tokens), 'v2 decision.tokensを空にできません')
    for case in objects(design.get('cases'), 'ui.cases'):
        name = h.nonempty(case.get('id'), 'case.id')
        h.require(name not in cases, 'case IDが重複しています')
        h.require(isinstance(case.get('scenario'), str) and case['scenario'] in scenarios, 'case.scenarioが不明です')
        h.require(unique(case.get('principles'), 'case.principles', 1) <= PRINCIPLES, 'case.principlesが不明です')
        h.require(unique(case.get('tokens'), 'case.tokens') <= selected_tokens, 'case.tokensは選択tokenが必要です')
        h.nonempty(case.get('question'), 'case.question')
        h.nonempty(case.get('target'), 'case.target')
        h.require(case.get('kind') in ('assertion', 'visual'), 'case.kindはassertion/visualです')
        if case['kind'] == 'assertion':
            expectation(case.get('expectation'), name)
            for token in case['tokens']:
                h.require(token in tokens and (tokens[token] is None or matches(tokens[token], case['expectation'])),
                          'token具体値・型・単位がcaseのexpectationと不一致です')
        else:
            h.require(not case['tokens'], 'token照合にはassertion caseが必要です')
        cases[name] = case
    h.require({c['scenario'] for c in cases.values()} == scenarios, '全scenarioにcaseが必要です')
    h.require({t for c in cases.values() for t in c['tokens']} == selected_tokens, '選択tokenの実測caseが不足しています')
    principles = {}
    for principle in objects(design.get('principles'), 'ui.principles'):
        name = principle.get('id')
        h.require(isinstance(name, str) and name in PRINCIPLES and name not in principles, 'principle IDが不明・重複しています')
        status = principle.get('status')
        h.require(status in ('applicable', 'inherited', 'not_applicable'), 'principle.statusが不正です')
        h.nonempty(principle.get('decision'), name+'.decision')
        for ref in objects(principle.get('source_refs'), name+'.source_refs'):
            reference(root, ref, name+'.source_refs', () if status == 'inherited' else deferred)
        expected = {c['id'] for c in cases.values() if name in c['principles']}
        case_ids = unique(principle.get('case_ids'), name+'.case_ids', int(status != 'not_applicable'))
        h.require(case_ids == expected, name+': principleとcaseの対応が不一致です')
        details = principle.get('details')
        h.require(isinstance(details, dict), name+'.detailsが必要です')
        if status == 'not_applicable':
            h.require(name == 'states_actions', name+': 視覚UIの必須原則を非適用にできません')
            h.nonempty(details.get('reason'), name+'.details.reason')
            h.require(not case_ids, name+': 非適用にcaseを指定できません')
        else:
            validate_details(root, identifier, name, details, cases, case_ids, registry, request_ids, deferred)
        principles[name] = principle
    h.require(set(principles) == PRINCIPLES, '10個すべてのUI principlesが必要です')
    h.require(selected_tokens <= set(tokens), 'tokenが不明です')
    if schema_version == 3:
        validate_quality(root, design, cases, snapshot)
    return cases


def validate_details(root, identifier, name, details, cases, allowed, registry, request_ids, deferred):
    def text(key, record=details):
        return h.nonempty(record.get(key), name+'.'+key)

    def links(record, key='case_ids', assertion=False):
        ids = unique(record.get(key), name+'.'+key, 1)
        h.require(ids <= allowed, name+': detailsのcase参照が不正です')
        if assertion:
            h.require(all(cases[i]['kind'] == 'assertion' for i in ids), name+': assertion caseが必要です')
        return ids

    if name == 'meaning':
        text('primary_action')
        for key in ('objects', 'states', 'risks'):
            h.strings(details.get(key), name+'.'+key, 1)
        links(details)
    elif name == 'structure':
        ref = details.get('wireframe_ref')
        reference(root, ref, 'structure.wireframe_ref')
        h.require(ref['path'].startswith(f'.harness/changes/{identifier}/inputs/'), 'wireframeは実装前のinputsに保存してください')
        for group in objects(details.get('groups'), 'structure.groups'):
            for key in ('id', 'comparison_axis', 'primary_action_location'):
                text(key, group)
            h.strings(group.get('members'), 'structure.members', 1)
    elif name == 'reuse':
        known = {c['id'] for c in registry['components']}
        for component in objects(details.get('components'), 'reuse.components'):
            h.require(isinstance(component.get('component'), str) and component['component'] in known, 'reuse.componentが不明です')
            reference(root, component.get('existing_ref'), 'reuse.existing_ref')
            h.require(component.get('choice') in ('reuse', 'new'), 'reuse.choiceはreuse/newです')
            for key in ('standard_alternative', 'reason', 'difference'):
                text(key, component)
            h.strings(component.get('uses'), 'reuse.uses', 1)
    elif name == 'visual_hierarchy':
        unique(details.get('order'), 'visual_hierarchy.order', 1)
        text('reason')
        links(details)
    elif name == 'tokens':
        bound = set()
        for binding in objects(details.get('bindings'), 'tokens.bindings'):
            token = text('token', binding)
            target = text('target', binding)
            for case_id in links(binding, assertion=True):
                h.require(token in cases[case_id]['tokens'] and cases[case_id]['target'] == target, 'tokens bindingとcaseが不一致です')
            bound.add(token)
        h.require(bound == {t for case in cases.values() for t in case['tokens']}, 'tokens bindingが不足しています')
    elif name == 'density_typography':
        dimensions = set()
        measured_dimensions = {}
        for measure in objects(details.get('measurements'), 'density_typography.measurements'):
            dimension = text('dimension', measure)
            h.require(dimension in DIMENSIONS, 'density_typography.dimensionが不明です')
            dimensions.add(dimension)
            target = text('target', measure)
            text('purpose', measure)
            for case_id in links(measure, assertion=True):
                h.require(measured_dimensions.get(case_id, dimension) == dimension,
                          '異なるdimensionの寸法に同じ実測caseを再利用できません')
                measured_dimensions[case_id] = dimension
                h.require(cases[case_id]['target'] == target and cases[case_id]['expectation']['operator'] == 'range',
                          'density_typographyには対象ごとのrange実測caseが必要です')
        h.require(dimensions == DIMENSIONS, 'density_typographyの5寸法が不足しています')
    elif name == 'copy':
        inventory_ids = links(details, 'inventory_case_ids', assertion=True)
        inventories = {case_id: [] for case_id in inventory_ids}
        for item in objects(details.get('items'), 'copy.items'):
            content = text('text', item)
            item_cases = unique(item.get('case_ids', list(inventory_ids)), 'copy.item.case_ids', 1)
            h.require(item_cases <= inventory_ids, 'copy.item.case_idsはinventory caseが必要です')
            for case_id in item_cases:
                inventories[case_id].append(content)
            h.require(item.get('role') in ('name','data','label','status','error','explanation','decoration'), 'copy.roleが不正です')
            h.require(isinstance(item.get('requirement'), str) and item['requirement'] in request_ids, 'copy.requirementが不明です')
            text('reason', item)
            if item['role'] in ('explanation','decoration'):
                text('alternative', item)
                reference(root, item.get('source_ref'), 'copy.source_ref')
        for case_id, inventory in inventories.items():
            h.require(cases[case_id]['expectation'] == {'operator':'equals', 'value':inventory}, 'copy inventoryの期待値が表示文一覧と異なります')
    elif name == 'states_actions':
        links(details, 'consistency_case_ids', assertion=True)
        action_ids = set()
        for action in objects(details.get('actions'), 'states_actions.actions'):
            action_id = text('id', action)
            h.require(action_id not in action_ids, 'action IDが重複しています')
            action_ids.add(action_id)
            text('entrypoint', action)
            outcomes = set()
            for outcome in objects(action.get('outcomes'), 'action.outcomes'):
                kind = outcome.get('outcome')
                h.require(isinstance(kind, str) and kind in OUTCOMES and kind not in outcomes, 'action outcomeが不明・重複しています')
                outcomes.add(kind)
                h.require(type(outcome.get('applicable')) is bool, 'outcome.applicableはboolです')
                text('reason', outcome)
                if outcome['applicable']:
                    links(outcome, assertion=True)
                else:
                    h.require(outcome.get('case_ids') == [], '非適用outcomeのcase_idsは空です')
            h.require(outcomes == OUTCOMES, 'actionの6個のoutcomesが不足しています')
    elif name == 'accessibility':
        aspects = set()
        for check in objects(details.get('checks'), 'accessibility.checks'):
            aspect = text('aspect', check)
            h.require(aspect in ASPECTS, 'accessibility.aspectが不明です')
            aspects.add(aspect)
            text('target', check)
            links(check, assertion=True)
        h.require(aspects == ASPECTS, 'accessibilityの確認対象が不足しています')
    elif name == 'scope_connections':
        for key in ('changed', 'related'):
            for path in h.strings(details.get(key), name+'.'+key, int(key == 'changed')):
                target = h.safe_path(root, path)
                h.require(target.is_file() or path in deferred, name+': 実在する対象が必要です')
        for key in ('state_owner','boundaries','complexity'):
            text(key)
        for connection in objects(details.get('connections'), 'scope_connections.connections'):
            text('entrypoint', connection)
            reference(root, connection.get('handler_ref'), 'scope_connections.handler_ref', deferred, anchor_only=True)
            h.require(connection.get('status') in ('mock','partial','unimplemented','production'), 'connection.statusが不正です')
            links(connection, assertion=True)


def collect_cases(root, provider_directory, entry, design, files, registry):
    expected = {c['id']:c for c in design['cases'] if c['scenario'] == entry['id']}
    attachments = {f['path'] for f in files if f['kind'] in ('metrics','aria','trace')}
    token_values = {t['id']:reference(root, t['source_ref'], 'token '+t['id']) for t in registry['tokens']}
    results = []
    seen = set()
    for result in objects(entry.get('case_results'), 'provider.case_results'):
        name = result.get('id')
        h.require(isinstance(name, str) and name in expected and name not in seen, 'case_resultが不明・重複・他scenarioです')
        seen.add(name)
        observation = h.nonempty(result.get('observation'), 'case_result.observation')
        ref = result.get('value_ref')
        h.require(isinstance(ref, dict) and 'pointer' in ref, 'case_result.value_refにはpath/pointerが必要です')
        path = h.safe_path(provider_directory, ref.get('path'))
        relative = path.relative_to(root).as_posix()
        h.require(relative in attachments, 'value_refは同じscenario/runのmetrics/aria/trace添付が必要です')
        try:
            raw = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError, UnicodeError) as exc:
            raise h.GateError('value_refのJSON証跡を読めません') from exc
        actual = pointer_value(raw, ref['pointer'], 'value_ref')
        case = expected[name]
        passed = case['kind'] == 'visual' or matches(actual, case['expectation'])
        if case['kind'] == 'visual':
            h.require(actual is not None and actual != '' and actual != [] and actual != {}, 'visual caseの観測値が空です')
        for token in case['tokens']:
            passed &= equal(actual, token_values[token])
        results.append({'id':name, 'observation':observation, 'value_ref':{'path':relative, 'pointer':ref['pointer']},
                        'actual':actual, 'status':('observed' if case['kind'] == 'visual' else 'passed') if passed else 'failed', 'kind':case['kind']})
    h.require(seen == set(expected), '必要なcase_resultsが未実行です')
    return results


def quality_records(design):
    details = {p['id']: p['details'] for p in design['principles']}
    return {'measurements': details['density_typography']['measurements'],
            'controls': details['density_typography'].get('controls'), 'copy': details['copy']['items']}


def control_cases(control):
    ids = unique(control.get('activation_case_ids'), 'control.activation_case_ids', 1)
    for region in ('visual', 'hit'):
        value = control.get(region)
        h.require(isinstance(value, dict), 'control.'+region+'が必要です')
        h.nonempty(value.get('target'), 'control.'+region+'.target')
        for axis in ('width', 'height'):
            ids |= unique(value.get(axis+'_case_ids'), 'control.'+region+'.'+axis+'_case_ids', 1)
    return ids


def validate_quality(root, design, cases, snapshot):
    """V3 extends existing evidence, separating visual adequacy from target activation."""
    records = quality_records(design)
    details = {p['id']: p['details'] for p in design['principles']}
    density = details['density_typography']
    for group, entries in records.items():
        seen = set()
        for item in objects(entries, 'v3.'+group, int(group != 'controls')):
            name = h.nonempty(item.get('id'), 'v3.'+group+'.id')
            h.require(name not in seen, 'v3.'+group+': IDが重複しています')
            seen.add(name)
    action_principle = next(p for p in design['principles'] if p['id'] == 'states_actions')
    declared_actions = details['states_actions'].get('actions', [])
    if action_principle['status'] == 'not_applicable':
        h.require(declared_actions == [], '非操作画面のactionsは空である必要があります')
    actions = {a['id']: a for a in objects(declared_actions, 'v3.actions', 0)}
    if action_principle['status'] == 'not_applicable':
        h.require(not records['controls'], '非操作画面にcontrolsを指定できません')
        h.nonempty(density.get('controls_reason'), 'density_typography.controls_reason')
    entrypoints = {name: unique(action.get('entrypoints', [action['entrypoint']]), 'action.entrypoints', 1)
                  for name, action in actions.items()}
    for name, action in actions.items():
        h.require(action['entrypoint'] in entrypoints[name], 'action.entrypointsにはprimary entrypointも必要です')
    covered_entrypoints = {name: set() for name in actions}
    density_cases = set(next(p['case_ids'] for p in design['principles'] if p['id'] == 'density_typography'))
    for control in records['controls']:
        control_cases(control)
        action = control.get('action')
        h.require(isinstance(action, str) and action in actions, 'control.actionが不明です')
        h.nonempty(control.get('reason'), 'control.reason')
        h.require(control['hit']['target'] in entrypoints[action], 'control.hit.targetとaction.entrypointが異なります')
        covered_entrypoints[action].add(control['hit']['target'])
        scenario_sets = []
        for region in ('visual', 'hit'):
            value = control[region]
            for axis in ('width', 'height'):
                ids = unique(value[axis+'_case_ids'], 'control dimension cases', 1)
                h.require(ids <= density_cases, 'control寸法はdensity_typographyのcaseが必要です')
                scenario_sets.append({cases[i]['scenario'] for i in ids})
                h.require(len(scenario_sets[-1]) == len(ids), 'control寸法はscenarioごとに1つの実測が必要です')
                for case_id in ids:
                    case = cases[case_id]
                    h.require(case['kind'] == 'assertion' and case['target'] == value['target'] and
                              case.get('dimension') == axis and case['expectation']['operator'] == 'range',
                              'control寸法には同じ対象・axisの数値range実測caseが必要です')
        ids = unique(control['activation_case_ids'], 'control.activation_case_ids', 1)
        h.require(ids <= set(action_principle['case_ids']), 'control activationはstates_actionsのcaseが必要です')
        scenario_sets.append({cases[i]['scenario'] for i in ids})
        h.require(len(scenario_sets[-1]) == len(ids) and all(s == scenario_sets[0] for s in scenario_sets),
                  'controlのvisual/hit/activationは同じscenarioが必要です')
        for case_id in ids:
            case = cases[case_id]
            h.require(case['kind'] == 'assertion' and case['target'] == control['hit']['target'] and
                      case.get('action') == action and equal(case['expectation'], {'operator': 'equals', 'value': True}),
                      'control activationは対象領域から実際のaction成功をtrueで検証してください')
    h.require(covered_entrypoints == entrypoints, '全action entrypointにcontrolが必要です')
    for item in records['copy']:
        purpose = item.get('purpose')
        h.require(isinstance(purpose, str) and purpose in ('identity', 'data', 'action_label', 'state_guidance',
                  'error_guidance', 'explanation', 'encouragement', 'decoration'), 'copy.purposeが不正です')
        reference(root, item.get('source_ref'), 'copy.source_ref')
        for key in ('alternative', 'redundancy'):
            h.nonempty(item.get(key), 'copy.'+key)
        if purpose in ('encouragement', 'decoration'):
            validate_authorization(root, item, snapshot, details['copy']['inventory_case_ids'])


def validate_authorization(root, item, snapshot, inventory=()):
    ref = item.get('authorization_ref')
    h.require(isinstance(ref, dict), 'copy.authorization_refが必要です')
    h.require(ref.get('provenance') in ('original_brief', 'baseline_specification'),
              'copy.authorization_ref.provenanceは原依頼・既存仕様が必要です')
    h.require(isinstance(snapshot, dict), 'copy authorizationには実装前snapshotが必要です')
    frozen = {}
    for key in ('source_digests', 'input_digests', 'requirements_digests'):
        values = snapshot.get(key, {})
        h.require(isinstance(values, dict), 'snapshot.'+key+'はオブジェクトである必要があります')
        frozen.update(values)
    registry_path = h.safe_path(root, snapshot.get('registry_path')).resolve().relative_to(root.resolve()).as_posix()
    excluded = {registry_path} | unique(snapshot.get('implementation_paths'), 'snapshot.implementation_paths')
    path = ref.get('path')
    h.require(isinstance(path, str) and path in frozen,
              'copy authorizationは実装前に固定した原依頼・既存仕様を参照してください')
    target = h.safe_path(root, path)
    h.require(target.resolve().relative_to(root.resolve()).as_posix() not in excluded,
              'copy authorizationに実装・アプリ定義元を使用できません')
    h.require(target.is_file() and h.file_sha(target) == frozen[path], 'copy authorizationの指紋が変わっています')
    source = reference(root, ref, 'copy.authorization_ref')
    mode = ref.get('mode', 'exact_text')
    h.require(mode in ('exact_text', 'commissioned_copy'), 'copy authorization.modeが不正です')
    if mode == 'exact_text':
        h.require(equal(source, item['text']), 'copy authorizationは表示する正確な文言への許可が必要です')
    else:
        h.require(ref['provenance'] == 'original_brief', 'copy commissionは原依頼を参照してください')
        h.nonempty(source, 'copy commission.directive')
        scope = ref.get('scope')
        h.require(isinstance(scope, dict), 'copy commission.scopeが必要です')
        h.nonempty(scope.get('description'), 'copy commission.scope.description')
        h.require(scope.get('purpose') == item['purpose'] and
                  unique(scope.get('case_ids'), 'copy commission.scope.case_ids', 1) == set(item.get('case_ids', inventory)),
                  'copy commission.scopeと表示目的・状態が異なります')


def validate_quality_review(review, design, measured):
    assessments = review.get('expectation_assessments')
    h.require(isinstance(assessments, dict), 'review.ui.expectation_assessmentsが必要です')
    records = quality_records(design)
    cases = {c['id']: c for c in design['cases']}
    inventory = next(p['details']['inventory_case_ids'] for p in design['principles'] if p['id'] == 'copy')
    for group, entries in records.items():
        expected = {item['id']: item for item in entries}
        seen = set()
        for assessment in objects(assessments.get(group), 'review.assessments.'+group, 0):
            name = assessment.get('id')
            h.require(isinstance(name, str) and name in expected and name not in seen, 'review assessment IDが不明・重複しています')
            seen.add(name)
            record = expected[name]
            ids = control_cases(record) if group == 'controls' else set(record.get('case_ids', inventory))
            h.require(unique(assessment.get('case_ids'), 'review.assessment.case_ids', 1) == ids and ids <= measured,
                      'review assessmentの実測case確認が不足しています')
            for key in ('evidence', 'rationale'):
                h.nonempty(assessment.get(key), 'review.assessment.'+key)
            if group == 'copy':
                h.require(assessment.get('text') == record['text'] and assessment.get('purpose') == record['purpose'],
                          'review copyのtext/purposeが現設計と異なります')
                h.require(equal(assessment.get('source_ref'), record['source_ref']), 'review copyの根拠が現設計と異なります')
                judgments = ('purpose_appropriate', 'source_supported', 'necessary', 'redundancy_justified')
            else:
                h.require(equal(assessment.get('expectations'), {i: cases[i]['expectation'] for i in ids}),
                          'review assessmentの期待値が現設計と異なります')
                judgments = ('bounds_appropriate',) if group == 'measurements' else ('visual_appropriate', 'hit_appropriate', 'activation_associated')
            h.require(all(assessment.get(key) is True for key in judgments), 'review assessmentの妥当性判断が合格していません')
        h.require(seen == set(expected), '全'+group+'に期待値自体のreview assessmentが必要です')


def validate_review(review, design, evidence, *, schema_version=2):
    expected = {p['id']:p for p in design['principles']}
    measured = {c['id'] for s in evidence['scenarios'] for c in s['case_results']}
    seen = set()
    for item in objects(review.get('principles'), 'review.ui.principles'):
        name = item.get('id')
        h.require(isinstance(name, str) and name in expected and name not in seen, 'review principleが不明・重複しています')
        seen.add(name)
        cases = unique(item.get('case_ids'), 'review.principle.case_ids')
        h.require(cases == set(expected[name]['case_ids']) and cases <= measured, 'review principleの実測case確認が不足しています')
        h.strings(item.get('observations'), 'review.principle.observations', 1)
        h.require(item.get('status') == 'passed', 'review principleがpassedではありません')
        h.require(h.strings(item.get('excess'), 'review.principle.excess') == [] and
                  h.strings(item.get('missing'), 'review.principle.missing') == [], 'review principleに未解決の過剰・不足があります')
    h.require(seen == PRINCIPLES, 'reviewに10個すべてのprinciplesが必要です')

    if schema_version == 3:
        validate_quality_review(review, design, measured)
