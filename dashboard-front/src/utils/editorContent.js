const EDITOR_JS_VERSION = "2.31.7";

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function inlineContentToHtml(content) {
  if (typeof content === "string") return escapeHtml(content);
  if (!Array.isArray(content)) return "";

  return content.map((item) => {
    if (item?.type === "link") {
      const href = escapeHtml(item.href ?? "");
      return `<a href="${href}">${inlineContentToHtml(item.content)}</a>`;
    }
    if (item?.type !== "text") return "";

    let html = escapeHtml(item.text ?? "").replaceAll("\n", "<br>");
    const styles = item.styles ?? {};
    if (styles.code) html = `<code>${html}</code>`;
    if (styles.bold) html = `<strong>${html}</strong>`;
    if (styles.italic) html = `<em>${html}</em>`;
    if (styles.underline) html = `<u>${html}</u>`;
    if (styles.strike) html = `<s>${html}</s>`;
    return html;
  }).join("");
}

function inlineContentToText(content) {
  if (typeof content === "string") return content;
  if (!Array.isArray(content)) return "";
  return content.map((item) => {
    if (item?.type === "link") return inlineContentToText(item.content);
    return item?.type === "text" ? (item.text ?? "") : "";
  }).join("");
}

function listItem(block) {
  return {
    content: inlineContentToHtml(block.content),
    meta: {},
    items: (block.children ?? []).map(listItem),
  };
}

function fileData(props = {}) {
  const name = props.name || props.caption || "첨부파일";
  const extension = name.includes(".") ? name.split(".").pop().slice(0, 10) : "";
  return {
    url: props.url ?? "",
    name,
    size: Number.isFinite(props.size) ? props.size : 0,
    extension,
  };
}

function convertBlock(block) {
  const props = block.props ?? {};

  if (block.type === "paragraph") {
    return { type: "paragraph", data: { text: inlineContentToHtml(block.content) } };
  }
  if (block.type === "heading") {
    return {
      type: "header",
      data: { text: inlineContentToHtml(block.content), level: props.level ?? 2 },
    };
  }
  if (["bulletListItem", "numberedListItem", "checkListItem"].includes(block.type)) {
    return {
      type: "list",
      data: {
        style: block.type === "numberedListItem" ? "ordered" : "unordered",
        meta: {},
        items: [listItem(block)],
      },
    };
  }
  if (block.type === "quote") {
    return {
      type: "quote",
      data: { text: inlineContentToHtml(block.content), caption: "", alignment: "left" },
    };
  }
  if (block.type === "codeBlock") {
    return { type: "code", data: { code: inlineContentToText(block.content) } };
  }
  if (block.type === "image") {
    return {
      type: "image",
      data: {
        file: { url: props.url ?? "" },
        caption: escapeHtml(props.caption ?? ""),
        withBorder: false,
        withBackground: false,
        stretched: props.previewWidth === undefined,
      },
    };
  }
  if (block.type === "file") {
    return {
      type: "attaches",
      data: { file: fileData(props), title: escapeHtml(props.caption ?? "") },
    };
  }
  if (block.type === "divider") return { type: "delimiter", data: {} };
  return null;
}

function mergeAdjacentLists(blocks) {
  return blocks.reduce((result, block) => {
    const previous = result.at(-1);
    if (block.type === "list" && previous?.type === "list" && previous.data.style === block.data.style) {
      previous.data.items.push(...block.data.items);
    } else {
      result.push(block);
    }
    return result;
  }, []);
}

export function blockNoteToEditorJs(blocks, time = Date.now()) {
  const converted = (blocks ?? []).map(convertBlock).filter(Boolean);
  return { time, blocks: mergeAdjacentLists(converted), version: EDITOR_JS_VERSION };
}

export function serializeForBlog(blocks, time = Date.now()) {
  return JSON.stringify(blockNoteToEditorJs(blocks, time));
}

function htmlToText(value = "") {
  if (typeof document === "undefined") return String(value).replace(/<[^>]*>/g, "");
  const element = document.createElement("div");
  element.innerHTML = value;
  return element.textContent ?? "";
}

function editorListItems(items = [], type = "bulletListItem") {
  return items.map((item) => ({
    type,
    content: htmlToText(typeof item === "string" ? item : item.content),
    children: editorListItems(item?.items, type),
  }));
}

export function editorJsToBlockNote(content = "") {
  let source;
  try { source = JSON.parse(content); } catch { return [{ type: "paragraph", content: htmlToText(content) }]; }
  if (!Array.isArray(source.blocks)) return [{ type: "paragraph", content: htmlToText(content) }];

  const blocks = source.blocks.flatMap((block) => {
    const data = block.data ?? {};
    if (block.type === "paragraph") return [{ type: "paragraph", content: htmlToText(data.text) }];
    if (block.type === "header") return [{ type: "heading", props: { level: Math.min(3, Math.max(1, data.level ?? 2)) }, content: htmlToText(data.text) }];
    if (block.type === "list") return editorListItems(data.items, data.style === "ordered" ? "numberedListItem" : "bulletListItem");
    if (block.type === "code") return [{ type: "codeBlock", content: data.code ?? "" }];
    if (block.type === "quote") return [{ type: "paragraph", content: htmlToText(data.text) }];
    if (block.type === "image") return [{ type: "image", props: { url: data.file?.url ?? "", caption: htmlToText(data.caption) } }];
    if (block.type === "attaches") return [{ type: "file", props: { url: data.file?.url ?? "", name: data.file?.name ?? "첨부파일", caption: htmlToText(data.title) } }];
    return [];
  });
  return blocks.length ? blocks : [{ type: "paragraph", content: "" }];
}

