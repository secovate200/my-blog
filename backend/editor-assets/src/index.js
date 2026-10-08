import AttachesTool from "@editorjs/attaches";
import CodeTool from "@editorjs/code";
import Delimiter from "@editorjs/delimiter";
import Embed from "@editorjs/embed";
import EditorJS from "@editorjs/editorjs";
import Header from "@editorjs/header";
import ImageTool from "@editorjs/image";
import InlineCode from "@editorjs/inline-code";
import EditorjsList from "@editorjs/list";
import Marker from "@editorjs/marker";
import Quote from "@editorjs/quote";
import Table from "@editorjs/table";
import Underline from "@editorjs/underline";
import Warning from "@editorjs/warning";

const toolIcon = (label) => `<svg width="20" height="20" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><rect x="1" y="3" width="18" height="14" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><text x="10" y="13" text-anchor="middle" font-size="7" fill="currentColor">${label}</text></svg>`;

class VideoTool {
  static get toolbox() { return { title: "영상", icon: toolIcon("▶") }; }
  static get isReadOnlySupported() { return true; }
  constructor({ data = {}, readOnly = false }) { this.data = data; this.readOnly = readOnly; }
  render() {
    const holder = document.createElement("div");
    holder.className = "editorjs-url-tool";
    const url = document.createElement("input");
    url.type = "url"; url.placeholder = "YouTube 또는 Vimeo URL"; url.value = this.data.url ?? ""; url.disabled = this.readOnly;
    const caption = document.createElement("input");
    caption.type = "text"; caption.placeholder = "영상 설명 (선택)"; caption.value = this.data.caption ?? ""; caption.disabled = this.readOnly;
    holder.append(url, caption); this.url = url; this.caption = caption;
    return holder;
  }
  save() { return { url: this.url.value.trim(), caption: this.caption.value.trim() }; }
  validate(data) { return /^https?:\/\//i.test(data.url); }
}

class LinkCardTool {
  static get toolbox() { return { title: "링크 카드", icon: toolIcon("↗") }; }
  static get isReadOnlySupported() { return true; }
  constructor({ data = {}, readOnly = false }) { this.data = data; this.readOnly = readOnly; }
  render() {
    const holder = document.createElement("div"); holder.className = "editorjs-url-tool";
    for (const [name, type, placeholder] of [["url", "url", "https:// 링크 주소"], ["title", "text", "링크 제목"], ["description", "text", "링크 설명 (선택)"]]) {
      const input = document.createElement("input"); input.type = type; input.placeholder = placeholder; input.value = this.data[name] ?? ""; input.disabled = this.readOnly; holder.append(input); this[name] = input;
    }
    return holder;
  }
  save() { return { url: this.url.value.trim(), title: this.title.value.trim(), description: this.description.value.trim() }; }
  validate(data) { return /^https?:\/\//i.test(data.url); }
}

class HeadingMenuTool extends Header {
  static get pasteConfig() {
    return undefined;
  }
}

const HeadingTools = Object.fromEntries(
  [1, 2, 3, 4, 5, 6].map((level) => [
    `heading${level}`,
    {
      class: HeadingMenuTool,
      toolbox: { ...Header.toolbox, title: `H${level}` },
      inlineToolbar: true,
      config: { levels: [level], defaultLevel: level },
    },
  ]),
);

function csrfToken() {
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith("csrftoken="))
    ?.split("=")[1];
}

function assetUrl(value = "") {
  try {
    const url = new URL(value, window.location.origin);
    if (/^\/blog\/assets\/[0-9a-f-]+\/(?:content|download)\/$/i.test(url.pathname)) {
      return `${url.pathname}${url.search}`;
    }
  } catch {
    // Editor.js will surface malformed values in the same way as before.
  }
  return value;
}

async function uploadFile(file) {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch("/blog/assets/upload/", {
    method: "POST",
    body,
    headers: { "X-CSRFToken": decodeURIComponent(csrfToken() ?? "") },
    credentials: "same-origin",
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.message || "파일 업로드에 실패했습니다.");
  if (result.file?.url) result.file.url = assetUrl(result.file.url);
  return result;
}

function initialData(value) {
  try {
    const data = JSON.parse(value);
    if (Array.isArray(data.blocks)) {
      data.blocks = data.blocks.map((block) => {
        if (block.type === "quote") {
          return {
              ...block,
              data: {
                ...block.data,
                text: trimEmptyLines(block.data.text),
                caption: trimEmptyLines(block.data.caption),
              },
            };
        }
        if (block.data?.file?.url) {
          return {
            ...block,
            data: {
              ...block.data,
              file: { ...block.data.file, url: assetUrl(block.data.file.url) },
            },
          };
        }
        return block;
      });
      return data;
    }
  } catch {
    // 기존 일반 텍스트는 아래에서 문단 블록으로 변환합니다.
  }
  return {
    blocks: value
      ? value.split(/\n{2,}/).map((text) => ({ type: "paragraph", data: { text } }))
      : [],
  };
}

function trimEmptyLines(html = "") {
  return html.replace(/^(?:\s*<br\s*\/?>(?:\s*))+|(?:(?:\s*)<br\s*\/?>\s*)+$/gi, "");
}

function initialize(textarea) {
  if (textarea.dataset.editorjsReady) return;
  textarea.dataset.editorjsReady = "true";

  const holder = document.createElement("div");
  holder.className = "editorjs-holder";
  textarea.hidden = true;
  textarea.parentNode.insertBefore(holder, textarea);
  holder.addEventListener("click", (event) => {
    const link = event.target.closest("a[href]");
    if (link) link.setAttribute("href", assetUrl(link.getAttribute("href")));
  });

  const editor = new EditorJS({
    holder,
    data: initialData(textarea.value),
    placeholder: "내용을 입력하거나 + 버튼으로 블록을 추가하세요.",
    tools: {
      header: {
        class: Header,
        toolbox: false,
        inlineToolbar: true,
        config: { levels: [1, 2, 3, 4, 5, 6], defaultLevel: 2 },
      },
      ...HeadingTools,
      list: { class: EditorjsList, inlineToolbar: true },
      quote: { class: Quote, inlineToolbar: true },
      table: { class: Table, inlineToolbar: true, config: { rows: 3, cols: 3, withHeadings: true } },
      warning: { class: Warning, inlineToolbar: true },
      video: VideoTool,
      linkCard: LinkCardTool,
      embed: {
        class: Embed,
        config: { services: { youtube: true, vimeo: true, codepen: true, coub: true, instagram: true, twitter: true, imgur: true } },
      },
      code: CodeTool,
      delimiter: Delimiter,
      marker: Marker,
      inlineCode: InlineCode,
      underline: Underline,
      image: {
        class: ImageTool,
        config: { uploader: { uploadByFile: uploadFile } },
      },
      attaches: {
        class: AttachesTool,
        config: { uploader: { uploadByFile: uploadFile } },
      },
    },
    i18n: {
      messages: {
        ui: {
          blockTunes: { toggler: { "Click to tune": "블록 설정", "or drag to move": "드래그하여 이동" } },
          inlineToolbar: { converter: { "Convert to": "블록 변환" } },
          toolbar: { toolbox: { Add: "블록 추가" } },
        },
        toolNames: {
          Text: "텍스트",
          Heading: "제목",
          List: "목록",
          Quote: "인용",
          Table: "표",
          Warning: "경고",
          Embed: "미디어 삽입",
          Code: "코드",
          Delimiter: "구분선",
          Image: "이미지",
          Attachment: "파일",
        },
      },
    },
    onChange: async () => {
      textarea.value = JSON.stringify(await editor.save());
    },
  });

  const form = textarea.form;
  form?.addEventListener("submit", async (event) => {
    if (form.dataset.editorjsSubmitting) return;
    event.preventDefault();
    textarea.value = JSON.stringify(await editor.save());
    form.dataset.editorjsSubmitting = "true";
    form.requestSubmit(event.submitter);
  });
}

function initializeAll(root = document) {
  root.querySelectorAll("textarea.editorjs-source").forEach(initialize);
}

document.addEventListener("DOMContentLoaded", () => initializeAll());
document.addEventListener("formset:added", (event) => initializeAll(event.target));
