function formatCNPJ(value) {
    const digits = value.replace(/\D/g, '').slice(0, 14);
    let out = '';
    for (let i = 0; i < digits.length; i++) {
        if (i === 2) out += '.';
        if (i === 5) out += '.';
        if (i === 8) out += '/';
        if (i === 12) out += '-';
        out += digits[i];
    }
    return out;
}

document.querySelectorAll('[data-mask="cnpj"]').forEach((el) => {
    el.addEventListener('input', function () {
        this.value = formatCNPJ(this.value);
    });
});

document.querySelectorAll('form').forEach((form) => {
    form.addEventListener('submit', function () {
        form.querySelectorAll('button[type="submit"]').forEach((btn) => {
            btn.disabled = true;
            btn.textContent = 'Enviando...';
        });
    });
});
