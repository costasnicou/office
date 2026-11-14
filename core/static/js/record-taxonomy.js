// Keep both subcategory levels and tags aligned with the selected scope.
const initializeRecordTaxonomy = () => {
    const form = document.querySelector('.record-form');
    if (!form) return;
    const category = form.elements.category;
    const subcategory = form.elements.subcategory;
    const child = form.elements.child_subcategory;
    const newCategory = form.elements.new_category;
    const newSubcategory = form.elements.new_subcategory;
    const newChild = form.elements.new_child_subcategory;
    const choices = [...form.querySelectorAll('input[name="tags"]')];
    const choiceSource = form.querySelector('.tag-choice-source');
    const choiceBank = choiceSource?.querySelector('#id_tags');
    const panels = [...form.querySelectorAll('[data-tag-level]')];
    const pendingByScope = new Map();
    const selectedName = select => [...select.options].find(option => option.value === select.value)?.textContent.trim() || '';
    const filterOptions = (select, allowed) => {
        for (const option of select.options) {
            if (!option.value) continue;
            option.hidden = !allowed(option);
            option.disabled = option.hidden;
            if (option.hidden && option.selected) select.value = '';
        }
    };
    const update = () => {
        filterOptions(subcategory, option => !newCategory.value.trim()
            && option.dataset.category === category.value);
        filterOptions(child, option => !newCategory.value.trim() && !newSubcategory.value.trim()
            && option.dataset.category === category.value && option.dataset.parent === subcategory.value);
        const tagScopes = new Set(['']);
        if (!newSubcategory.value.trim() && subcategory.value) tagScopes.add(subcategory.value);
        if (!newSubcategory.value.trim() && !newChild.value.trim() && child.value) tagScopes.add(child.value);
        const categoryName = newCategory.value.trim() || selectedName(category);
        const categoryKey = newCategory.value.trim() ? `new:${categoryName}` : category.value;
        const parentName = newSubcategory.value.trim() || selectedName(subcategory);
        const parentKey = newSubcategory.value.trim() ? `new:${parentName}` : subcategory.value;
        const childName = newChild.value.trim() || selectedName(child);
        const childKey = newChild.value.trim() ? `new:${childName}` : child.value;
        const scopes = {
            category: {active: !!categoryKey, name: categoryName, key: categoryKey, input: form.elements.new_category_tags},
            subcategory: {active: !!categoryKey && !!parentKey, name: parentName, key: `${categoryKey}/${parentKey}`, input: form.elements.new_subcategory_tags},
            child: {active: !!categoryKey && !!parentKey && !!childKey, name: childName, key: `${categoryKey}/${parentKey}/${childKey}`, input: form.elements.new_child_tags},
        };
        // Keep pending names attached to their scope when the category path changes.
        for (const panel of panels) {
            const scope = scopes[panel.dataset.tagLevel];
            const previous = panel.dataset.scopeKey;
            const next = scope.active ? scope.key : '';
            if (previous !== undefined && previous !== next) {
                pendingByScope.set(`${panel.dataset.tagLevel}:${previous}`, scope.input.value);
                scope.input.value = pendingByScope.get(`${panel.dataset.tagLevel}:${next}`) || '';
            }
            panel.dataset.scopeKey = next;
            panel.hidden = !scope.active;
            scope.input.disabled = !scope.active;
            panel.querySelector('.tag-scope-name').textContent = scope.active ? `— ${scope.name}` : '';
        }
        for (const checkbox of choices) {
            const visible = !newCategory.value.trim()
                && checkbox.dataset.category === category.value
                && tagScopes.has(checkbox.dataset.subcategory);
            checkbox.disabled = !visible;
            const label = checkbox.closest('label');
            const row = label.parentElement;
            row.hidden = !visible;
            if (!visible) checkbox.checked = false;
            if (panels.length) {
                const level = !checkbox.dataset.subcategory ? 'category'
                    : checkbox.dataset.subcategory === subcategory.value ? 'subcategory' : 'child';
                const destination = visible ? form.querySelector(`[data-tag-level="${level}"] .tag-level-options`) : choiceBank;
                destination?.append(row);
                const textNodes = [...label.childNodes].filter(node => node.nodeType === 3);
                textNodes.forEach((node, index) => {
                    node.textContent = index === textNodes.length - 1 ? ` ${checkbox.dataset.tagName}` : '';
                });
            }
        }
        for (const panel of panels) {
            panel.querySelector('.tag-level-empty').hidden = !!panel.querySelector('.tag-level-options input');
        }
        if (choiceSource) choiceSource.hidden = true;
        const prompt = form.querySelector('.tag-scope-prompt');
        if (prompt) prompt.hidden = scopes.category.active;

    };
    for (const field of [category, subcategory, child, newCategory, newSubcategory, newChild]) {
        field.addEventListener('change', update);
        field.addEventListener('input', update);
    }
    update();
};
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeRecordTaxonomy);
} else initializeRecordTaxonomy();
