/**
 * Editor.js JSON을 요약용 일반 텍스트로 변환합니다.
 * 이전 형식의 문자열도 지원하여 콘텐츠 형식 전환 중 호환성을 유지합니다.
 */
export function parseEditorContent(content = "") {
  try {
    const data = JSON.parse(content);
    return Array.isArray(data.blocks) ? data : null;
  } catch {
    return null;
  }
}

function listItemText(item) {
  if (typeof item === "string") return item;
  return `${item?.content ?? ""} ${(item?.items ?? []).map(listItemText).join(" ")}`;
}

export function contentToPlainText(content = "") {
  const editorData = parseEditorContent(content);
  const source = editorData
    ? editorData.blocks
        .map((block) => {
          if (block.type === "list") return (block.data.items ?? []).map(listItemText).join(" ");
          return block.data.text ?? block.data.code ?? block.data.caption ?? block.data.title ?? "";
        })
        .join(" ")
    : content;

  return source
    .replace(/<[^>]*>/g, " ")
    .replace(/!\[[^\]]*\]\([^)]*\)/g, " ")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/[`#>*_~]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}
