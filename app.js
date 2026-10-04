(() => {
  "use strict";

  const mapping = window.NIGHTREIGN_MAPPING;
  const resistanceData = window.NIGHTREIGN_RESISTANCES;
  const state = {
    selected: { day1: null, day2: null, event: null },
    search: { day1: "", day2: "", event: "" }
  };
  const typeClasses = {
    damage: { "標準": "type--standard", "斬撃": "type--slash", "打撃": "type--strike", "刺突": "type--pierce", "魔力": "type--magic", "炎": "type--fire", "雷": "type--lightning", "聖": "type--holy" },
    status: { "毒": "type--poison", "腐敗": "type--rot", "出血": "type--bleed", "凍傷": "type--frost", "睡眠": "type--sleep", "発狂": "type--madness" }
  };

  const elements = {
    reset: document.getElementById("reset-button"),
    day1Search: document.getElementById("day1-search"),
    day2Search: document.getElementById("day2-search"),
    eventSearch: document.getElementById("event-search"),
    day1Options: document.getElementById("day1-options"),
    day2Options: document.getElementById("day2-options"),
    eventOptions: document.getElementById("event-options"),
    day1Selected: document.getElementById("day1-selected"),
    day2Selected: document.getElementById("day2-selected"),
    eventSelected: document.getElementById("event-selected"),
    day1Empty: document.getElementById("day1-empty"),
    day2Empty: document.getElementById("day2-empty"),
    eventEmpty: document.getElementById("event-empty"),
    day1Section: document.getElementById("day1-section"),
    day2Section: document.getElementById("day2-section"),
    nightlordSection: document.getElementById("nightlord-section"),
    candidateCount: document.getElementById("candidate-count"),
    candidateMessage: document.getElementById("candidate-message"),
    candidateDetails: document.getElementById("candidate-details"),
    day1ResistanceDetails: document.getElementById("day1-resistance-details"),
    day2ResistanceDetails: document.getElementById("day2-resistance-details")
  };

  function findById(collection, id) {
    return collection.find((entry) => entry.id === id) || null;
  }

  function normalize(value) {
    return String(value || "").normalize("NFKC").toLocaleLowerCase("ja").trim();
  }

  function matchesSearch(entry, query) {
    const normalizedQuery = normalize(query);
    if (!normalizedQuery) return true;
    const searchable = [entry.name, ...(entry.aliases || [])].map(normalize).join(" ");
    return searchable.includes(normalizedQuery);
  }

  function intersect(left, right) {
    const rightSet = new Set(right);
    return left.filter((name) => rightSet.has(name));
  }

  function isNameresPossible(day1, day2) {
    const day1Possible = Boolean(day1 && mapping.namelessDay1Ids.includes(day1.id));
    const day2Possible = Boolean(day2 && mapping.namelessDay2Ids.includes(day2.id));
    return day1Possible && day2Possible;
  }

  function getCandidates(day1, day2, event) {
    if (!day1 && !day2 && !event) return [];

    let candidates = null;
    if (day1) candidates = [...day1.kings];
    if (day2) {
      if (day2.noBoss) {
        candidates = isNameresPossible(day1, day2) ? ["ナメレス"] : [];
      } else {
        candidates = candidates ? intersect(candidates, day2.kings) : [...day2.kings];
        if (isNameresPossible(day1, day2) && !candidates.includes("ナメレス")) {
          candidates.push("ナメレス");
        }
      }
    } else if (day1 && mapping.namelessDay1Ids.includes(day1.id) && !candidates.includes("ナメレス")) {
      candidates.push("ナメレス");
    }

    if (event) {
      candidates = candidates ? intersect(candidates, event.kings) : [...event.kings];
    }

    const available = new Set(candidates || []);
    return mapping.kings.filter((king) => available.has(king.name));
  }

  function getDay1Options() {
    const selectedDay2 = findById(mapping.day2, state.selected.day2);
    const selectedEvent = findById(mapping.events, state.selected.event);
    return mapping.day1.filter((entry) => getCandidates(entry, selectedDay2, selectedEvent).length > 0);
  }

  function getDay2Options() {
    const selectedDay1 = findById(mapping.day1, state.selected.day1);
    if (!selectedDay1) return [];
    const selectedEvent = findById(mapping.events, state.selected.event);
    return mapping.day2.filter((entry) => {
      const candidates = getCandidates(selectedDay1, entry, selectedEvent);
      return entry.noBoss
        ? candidates.some((king) => king.name === "ナメレス")
        : candidates.some((king) => king.name !== "ナメレス");
    });
  }

  function getEventOptions() {
    const selectedDay1 = findById(mapping.day1, state.selected.day1);
    const selectedDay2 = findById(mapping.day2, state.selected.day2);
    return mapping.events.filter((entry) => getCandidates(selectedDay1, selectedDay2, entry).length > 0);
  }

  function createElement(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function showSelected(container, entry, group, label) {
    container.replaceChildren();
    container.hidden = !entry;
    if (!entry) return;

    container.append(createElement("span", "selected-name", entry.name));
    const clearButton = createElement("button", "", "解除");
    clearButton.type = "button";
    clearButton.setAttribute("aria-label", `${label}「${entry.name}」を解除`);
    clearButton.addEventListener("click", () => select(group, null));
    container.append(clearButton);
  }

  function renderOptions(container, emptyHint, entries, options) {
    const { query, selectedId, group, disabled = false } = options;
    container.replaceChildren();
    container.setAttribute("aria-disabled", String(disabled));
    emptyHint.hidden = true;
    if (disabled) return;

    const visibleEntries = entries.filter((entry) => matchesSearch(entry, query));
    for (const entry of visibleEntries) {
      const button = createElement("button", "option-button", entry.name);
      button.type = "button";
      button.setAttribute("aria-pressed", String(entry.id === selectedId));
      button.addEventListener("click", () => select(group, entry.id === selectedId ? null : entry.id));
      container.append(button);
    }
    emptyHint.hidden = visibleEntries.length > 0;
  }

  function updateSelectionLists() {
    const selectedDay1 = findById(mapping.day1, state.selected.day1);
    const selectedDay2 = findById(mapping.day2, state.selected.day2);
    const selectedEvent = findById(mapping.events, state.selected.event);

    showSelected(elements.day1Selected, selectedDay1, "day1", "1日目");
    showSelected(elements.day2Selected, selectedDay2, "day2", "2日目");
    showSelected(elements.eventSelected, selectedEvent, "event", "イベント");

    const day2Disabled = !selectedDay1;
    elements.day2Search.disabled = day2Disabled;
    elements.day2Search.placeholder = day2Disabled ? "1日目を先に選択" : "ボス名";
    elements.day2Empty.textContent = "一致するボスがありません。";

    renderOptions(elements.day1Options, elements.day1Empty, getDay1Options(), { query: state.search.day1, selectedId: state.selected.day1, group: "day1" });
    renderOptions(elements.day2Options, elements.day2Empty, getDay2Options(), { query: state.search.day2, selectedId: state.selected.day2, group: "day2", disabled: day2Disabled });
    renderOptions(elements.eventOptions, elements.eventEmpty, getEventOptions(), { query: state.search.event, selectedId: state.selected.event, group: "event" });
  }

  function isStandardResistance(value, type) {
    return (type === "damage" && value === 0) || (type === "status" && value === 252);
  }

  function resolveResistanceValue(value, type) {
    if (value === null || value === undefined) {
      return { display: "—", effect: "unknown-cell", meaning: "資料なし" };
    }
    if (type === "damage" && typeof value === "number") {
      if (value > 0) return { display: "+" + value + "%", effect: "weakness-cell", meaning: "弱点" };
      if (value < 0) return { display: "−" + Math.abs(value) + "%", effect: "resist-cell", meaning: "耐性" };
      return { display: "0%", effect: "neutral-cell", meaning: "標準" };
    }
    if (type === "status" && value === "無効") {
      return { display: "無効", effect: "resist-cell", meaning: "付与無効" };
    }
    if (type === "status" && typeof value === "number") {
      const effect = value < 252 ? "weakness-cell" : value > 252 ? "resist-cell" : "neutral-cell";
      const meaning = getStatusBand(value) || (value < 252 ? "弱点" : value > 252 ? "耐性" : "標準");
      return { display: String(value), effect, meaning };
    }
    return { display: "—", effect: "unknown-cell", meaning: "資料なし" };
  }

  function addResistanceTable(parent, title, labels, values, options) {
    const { type, compact = false, showEmpty = false } = options;
    const rows = [];
    labels.forEach((label, index) => {
      const value = values[index];
      if (compact && isStandardResistance(value, type)) return;
      const resolved = resolveResistanceValue(value, type);
      const row = document.createElement("tr");
      const nameCell = createElement("th", typeClasses[type][label], label);
      nameCell.scope = "row";
      const valueCell = createElement("td", resolved.effect, resolved.display);
      valueCell.setAttribute("aria-label", resolved.display + "、" + resolved.meaning);
      row.append(nameCell, valueCell);
      rows.push(row);
    });

    if (!rows.length && !showEmpty) return false;
    const groupClass = "stat-group stat-group--" + type + (compact ? " quick-group" : "");
    const group = createElement("section", groupClass);
    group.append(createElement("h4", "", title));
    if (rows.length) {
      const table = createElement("table", "resistance-table" + (compact ? " quick-table" : ""));
      const body = createElement("tbody");
      body.append(...rows);
      table.append(body);
      group.append(table);
    }
    parent.append(group);
    return true;
  }
  function getStatusBand(value) {
    if (typeof value !== "number") return "";
    if (value <= 84) return "大弱点";
    if (value <= 154) return "弱点";
    if (value === 252) return "標準";
    if (value >= 542) return "強耐性";
    return "";
  }

  function createQuickResistanceSummary(records) {
    const summary = createElement("div", "quick-summary");
    records.forEach((record) => {
      const form = createElement("section", "quick-form");
      if (records.length > 1) {
        form.append(createElement("h5", "quick-form-name", record ? record.name : "—"));
      }
      if (!record) {
        const missing = createElement("div", "no-data-panel", "—");
        missing.setAttribute("aria-label", "資料なし");
        form.append(missing);
      } else {
        const groups = createElement("div", "quick-groups");
        const physicalLabels = resistanceData.damageLabels.slice(0, 4);
        const elementalLabels = resistanceData.damageLabels.slice(4);
        addResistanceTable(groups, "物理", physicalLabels, record.damage.slice(0, 4), { type: "damage", compact: true, showEmpty: true });
        addResistanceTable(groups, "属性", elementalLabels, record.damage.slice(4), { type: "damage", compact: true, showEmpty: true });
        addResistanceTable(groups, "状態異常", resistanceData.statusLabels, record.status, { type: "status", compact: true, showEmpty: true });
        if (groups.childElementCount) form.append(groups);
      }
      if (form.childElementCount) summary.append(form);
    });
    summary.hidden = !summary.childElementCount;
    return summary;
  }
  function appendRecordContent(parent, record, formTitle = "") {
    if (!record) {
      const missing = createElement("div", "no-data-panel", "—");
      missing.setAttribute("aria-label", "資料なし");
      parent.append(missing);
      return;
    }

    const block = createElement("section", "form-block");
    if (formTitle) block.append(createElement("h4", "form-title", formTitle));
    const grid = createElement("div", "stats-grid");
    addResistanceTable(grid, "物理・属性", resistanceData.damageLabels, record.damage, { type: "damage" });
    addResistanceTable(grid, "状態異常", resistanceData.statusLabels, record.status, { type: "status" });
    block.append(grid);
    parent.append(block);
  }

  function createBossDetails(summaryText, recordIds, fallbackName = "") {
    const details = createElement("details", "resistance-detail");
    const summary = createElement("summary", "");
    const records = recordIds.map((id) => resistanceData.records[id] || null);
    const heading = createElement("span", "detail-heading");
    heading.append(createElement("span", "detail-title", summaryText));
    summary.append(heading);
    const content = createElement("div", "detail-content");

    if (!recordIds.length) {
      if (fallbackName === "ボスなし") {
        content.append(createElement("div", "no-data-panel", "ボスなし"));
      } else {
        const missing = createElement("div", "no-data-panel", "—");
        missing.setAttribute("aria-label", "資料なし");
        content.append(missing);
      }
    } else if (recordIds.length > 1) {
      const forms = createElement("div", "forms-stack");
      for (const id of recordIds) {
        const record = resistanceData.records[id] || null;
        const formDetails = createElement("details", "form-detail");
        const formSummary = createElement("summary", "", record ? record.name : "—");
        if (!record) formSummary.setAttribute("aria-label", "資料なし");
        const formContent = createElement("div", "detail-content");
        appendRecordContent(formContent, record);
        formDetails.append(formSummary, formContent);
        forms.append(formDetails);
      }
      content.append(forms);
    } else {
      const stack = createElement("div", "forms-stack");
      const record = records[0];
      const displayName = record ? record.name : "資料なし";
      appendRecordContent(stack, record, recordIds.length > 1 ? displayName : "");
      content.append(stack);
      details.dataset.recordName = displayName;
    }

    details.append(summary, content);
    return details;
  }

  function renderCandidates() {
    const day1 = findById(mapping.day1, state.selected.day1);
    const day2 = findById(mapping.day2, state.selected.day2);
    const event = findById(mapping.events, state.selected.event);
    const hasInput = Boolean(day1 || day2 || event);
    const candidates = getCandidates(day1, day2, event);

    elements.candidateDetails.replaceChildren();
    elements.candidateCount.textContent = hasInput ? candidates.length + "体" : "未選択";

    if (!hasInput) {
      elements.candidateMessage.textContent = "";
      elements.candidateMessage.hidden = true;
      return;
    }
    if (!candidates.length) {
      elements.candidateMessage.textContent = "一致する候補はありません。";
      elements.candidateMessage.hidden = false;
      return;
    }

    elements.candidateMessage.textContent = "";
    elements.candidateMessage.hidden = true;
    for (const king of candidates) {
      const records = king.resistanceIds.map((id) => resistanceData.records[id] || null);
      const article = createElement("article", "candidate-card");
      const details = createBossDetails(king.name, king.resistanceIds);
      details.classList.add("candidate-detail");
      details.dataset.kingId = king.id;
      article.append(details, createQuickResistanceSummary(records));
      elements.candidateDetails.append(article);
    }
  }
  function renderEncounterResistances(entry, detailsElement) {
    detailsElement.replaceChildren();
    if (!entry) return;
    if (!entry.resistanceIds.length) {
      const fallback = entry.noBoss
        ? "ボスなし"
        : "資料なし";
      detailsElement.append(createBossDetails(entry.name, [], fallback));
      return;
    }

    for (const id of entry.resistanceIds) {
      const record = resistanceData.records[id] || null;
      const componentName = record ? record.name : "—";
      const details = createBossDetails(componentName, [id]);
      if (!record) details.querySelector("summary").setAttribute("aria-label", "資料なし");
      details.dataset.encounterId = entry.id;
      detailsElement.append(details);
    }
  }

  function renderSelectedResistances() {
    renderEncounterResistances(
      findById(mapping.day1, state.selected.day1),
      elements.day1ResistanceDetails
    );
    renderEncounterResistances(
      findById(mapping.day2, state.selected.day2),
      elements.day2ResistanceDetails
    );
  }

  function updateResetButton() {
    const hasSelection = Object.values(state.selected).some(Boolean);
    const hasSearch = Object.values(state.search).some(Boolean);
    elements.reset.disabled = !hasSelection && !hasSearch;
  }

  function render() {
    updateSelectionLists();
    renderCandidates();
    renderSelectedResistances();
    updateResetButton();
  }

  function select(group, id) {
    const previousDay1 = state.selected.day1;
    state.selected[group] = id;
    if (group === "day1" && id !== previousDay1) state.selected.day2 = null;
    if (group === "day1") {
      elements.day1Section.open = true;
      elements.day2Section.open = false;
    }
    if (group === "day2") elements.day2Section.open = Boolean(id);
    elements.nightlordSection.open = Object.values(state.selected).some(Boolean);
    render();
  }

  function bindSearch(input, key) {
    input.addEventListener("input", () => {
      state.search[key] = input.value;
      updateSelectionLists();
      updateResetButton();
    });
  }

  bindSearch(elements.day1Search, "day1");
  bindSearch(elements.day2Search, "day2");
  bindSearch(elements.eventSearch, "event");
  elements.reset.addEventListener("click", () => {
    state.selected.day1 = null;
    state.selected.day2 = null;
    state.selected.event = null;
    state.search.day1 = "";
    state.search.day2 = "";
    state.search.event = "";
    elements.day1Search.value = "";
    elements.day2Search.value = "";
    elements.eventSearch.value = "";
    elements.day1Section.open = true;
    elements.day2Section.open = false;
    elements.nightlordSection.open = false;
    render();
  });

  render();

  if ("serviceWorker" in navigator && location.protocol !== "file:") {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("./service-worker.js").catch(() => {});
    }, { once: true });
  }
})();
