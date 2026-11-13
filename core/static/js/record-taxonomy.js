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
        for (const checkbox of form.querySelectorAll('input[name="tags"]')) {
            const visible = !newCategory.value.trim() && !newSubcategory.value.trim() && !newChild.value.trim()
                && checkbox.dataset.category === category.value
                && checkbox.dataset.subcategory === (child.value || subcategory.value);
            checkbox.disabled = !visible;
            checkbox.closest('label').parentElement.hidden = !visible;
            if (!visible) checkbox.checked = false;
        }
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
