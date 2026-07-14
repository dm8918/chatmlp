export async function downloadMessagePdf(node: HTMLElement): Promise<void> {
  const { default: html2pdf } = await import("html2pdf.js");

  const wrapper = document.createElement("div");
  wrapper.className = "pdf-export";

  const header = document.createElement("div");
  header.className = "pdf-export__header";
  const date = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  header.innerHTML = `
    <div class="pdf-export__brand">Cerebro — Los Pelambres</div>
    <div class="pdf-export__date">${p(date.getDate())}-${p(
      date.getMonth() + 1,
    )}-${date.getFullYear()} ${p(date.getHours())}:${p(date.getMinutes())}</div>
  `;

  const body = node.cloneNode(true) as HTMLElement;

  wrapper.appendChild(header);
  wrapper.appendChild(body);
  document.body.appendChild(wrapper);

  const filename = `cerebro-respuesta-${date.getFullYear()}${p(
    date.getMonth() + 1,
  )}${p(date.getDate())}-${p(date.getHours())}${p(date.getMinutes())}.pdf`;

  try {
    await html2pdf()
      .set({
        margin: [15, 15, 18, 15],
        filename,
        image: { type: "jpeg", quality: 0.95 },
        html2canvas: { scale: 2, useCORS: true, backgroundColor: "#ffffff" },
        jsPDF: { unit: "mm", format: "a4", orientation: "portrait" },
        pagebreak: { mode: ["avoid-all", "css", "legacy"] },
      })
      .from(wrapper)
      .save();
  } finally {
    wrapper.remove();
  }
}
