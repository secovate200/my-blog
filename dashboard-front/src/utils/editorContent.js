function htmlToText(value = "") {
  if (typeof document === "undefined") {
    return String(value)
      .replace(/<br\s*\/?>/gi, "\n")
      .replace(/<[^>]*>/g, "")
      .replaceAll("&lt;", "<")
      .replaceAll("&gt;", ">")
      .replaceAll("&amp;", "&");
  }
  const element = document.createElement("div");
  element.innerHTML = value;
  return element.textContent ?? "";
}

export function editorJsToPlainText(editorDocument = {}) {
  const lines = (editorDocument.blocks ?? []).flatMap((block) => {
    const data = block.data ?? {};
    if (["paragraph", "header", "quote"].includes(block.type)) {
      return [htmlToText(data.text)];
    }
    if (block.type === "code") return [data.code ?? ""];
    if (block.type === "list") {
      const flatten = (items = []) => items.flatMap((item) => [
        htmlToText(typeof item === "string" ? item : item.content),
        ...flatten(item?.items),
      ]);
      return flatten(data.items);
    }
    if (block.type === "image") return [htmlToText(data.caption)];
    if (block.type === "attaches") {
      return [htmlToText(data.title || data.file?.name)];
    }
    return [];
  });
  return lines.filter(Boolean).join("\n\n");
}

export function normalizeEditorDocument(editorDocument = {}) {
  return {
    ...editorDocument,
    blocks: (editorDocument.blocks ?? []).map((block) => {
      const headingMatch = /^heading([1-6])$/.exec(block?.type ?? "");
      if (!headingMatch) return block;
      return {
        ...block,
        type: "header",
        data: { ...block.data, level: Number(headingMatch[1]) },
      };
    }),
  };
}
