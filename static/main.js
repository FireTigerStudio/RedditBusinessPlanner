document.addEventListener('click', async (e) => {
  if (e.target && e.target.id === 'copyBtn') {
    const raw = document.getElementById('mdRaw').innerText;
    try {
      await navigator.clipboard.writeText(raw);
      e.target.innerText = '已复制';
      setTimeout(() => (e.target.innerText = '复制Markdown'), 1500);
    } catch (_) {}
  }
  if (e.target && e.target.id === 'pdfBtn') {
    const element = document.getElementById('mdPreview');
    const opt = {
      margin:       10,
      filename:     'plan.pdf',
      image:        { type: 'jpeg', quality: 0.98 },
      html2canvas:  { scale: 2 },
      jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' }
    };
    html2pdf().from(element).set(opt).save();
  }
});
