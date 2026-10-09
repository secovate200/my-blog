import { useEffect, useRef } from "react";
import EditorJS from "@editorjs/editorjs";
import Header from "@editorjs/header";
import EditorjsList from "@editorjs/list";
import Quote from "@editorjs/quote";
import CodeTool from "@editorjs/code";
import ImageTool from "@editorjs/image";
import AttachesTool from "@editorjs/attaches";
import Delimiter from "@editorjs/delimiter";
import Embed from "@editorjs/embed";
import InlineCode from "@editorjs/inline-code";
import Marker from "@editorjs/marker";
import Table from "@editorjs/table";
import Underline from "@editorjs/underline";
import Warning from "@editorjs/warning";
import { uploadMedia } from "../../api";

const EMPTY_DOCUMENT = { blocks: [] };

const toolIcon = (label) => `<svg width="20" height="20" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><rect x="1" y="3" width="18" height="14" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><text x="10" y="13" text-anchor="middle" font-size="7" fill="currentColor">${label}</text></svg>`;

class VideoTool {
  static get toolbox() { return { title: "영상", icon: toolIcon("▶") }; }
  static get isReadOnlySupported() { return true; }
  constructor({ data = {}, readOnly = false }) { this.data = data; this.readOnly = readOnly; }
  render() {
    const holder = document.createElement("div");
    holder.className = "editorjs-url-tool";
    const url = document.createElement("input");
    url.type = "url";
    url.placeholder = "YouTube 또는 Vimeo URL";
    url.value = this.data.url ?? "";
    url.disabled = this.readOnly;
    const caption = document.createElement("input");
    caption.type = "text";
    caption.placeholder = "영상 설명 (선택)";
    caption.value = this.data.caption ?? "";
    caption.disabled = this.readOnly;
    holder.append(url, caption);
    this.url = url;
    this.caption = caption;
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
    const holder = document.createElement("div");
    holder.className = "editorjs-url-tool";
    const fields = [
      ["url", "url", "https:// 링크 주소"],
      ["title", "text", "링크 제목"],
      ["description", "text", "링크 설명 (선택)"],
    ];
    for (const [name, type, placeholder] of fields) {
      const input = document.createElement("input");
      input.type = type;
      input.placeholder = placeholder;
      input.value = this.data[name] ?? "";
      input.disabled = this.readOnly;
      holder.append(input);
      this[name] = input;
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

function legacyContentToDocument(content) {
  const source = String(content ?? "").trim();
  if (!source) return EMPTY_DOCUMENT;
  if (typeof document === "undefined") {
    return { blocks: [{ type: "paragraph", data: { text: source } }] };
  }

  const container = document.createElement("div");
  container.innerHTML = source;
  const blocks = Array.from(container.children).map((element) => {
    const tag = element.tagName.toLowerCase();
    if (/^h[1-6]$/.test(tag)) {
      return { type: "header", data: { text: element.innerHTML, level: Number(tag[1]) } };
    }
    if (tag === "pre") {
      return { type: "code", data: { code: element.textContent ?? "" } };
    }
    if (tag === "blockquote") {
      return { type: "quote", data: { text: element.innerHTML, caption: "", alignment: "left" } };
    }
    if (tag === "ul" || tag === "ol") {
      return {
        type: "list",
        data: {
          style: tag === "ol" ? "ordered" : "unordered",
          items: Array.from(element.children).map((item) => item.innerHTML),
        },
      };
    }
    return { type: "paragraph", data: { text: element.innerHTML } };
  });

  return {
    blocks: blocks.length
      ? blocks
      : [{ type: "paragraph", data: { text: container.innerHTML || source } }],
  };
}

function parseDocument(content) {
  if (!content) return EMPTY_DOCUMENT;
  try {
    const parsed = typeof content === "string" ? JSON.parse(content) : content;
    if (!Array.isArray(parsed?.blocks)) return EMPTY_DOCUMENT;
    return {
      ...parsed,
      blocks: parsed.blocks.map((block) => {
        const headingMatch = /^heading([1-6])$/.exec(block?.type ?? "");
        if (headingMatch) {
          block = {
            ...block,
            type: "header",
            data: { ...block.data, level: Number(headingMatch[1]) },
          };
        }
        const value = block?.data?.file?.url;
        if (!value) return block;
        try {
          const url = new URL(value, window.location.origin);
          if (!/^\/blog\/assets\/[0-9a-f-]+\/(?:content|download)\/$/i.test(url.pathname)) return block;
          return {
            ...block,
            data: { ...block.data, file: { ...block.data.file, url: `${url.pathname}${url.search}` } },
          };
        } catch {
          return block;
        }
      }),
    };
  } catch {
    return legacyContentToDocument(content);
  }
}

const uploadResponse = async (file) => ({
  success: 1,
  file: await uploadMedia(file),
});

export default function EditorJsEditor({ initialContent = "", editorRef, onError }) {
  const holderRef = useRef(null);

  useEffect(() => {
    if (!holderRef.current) return undefined;

    let editor = null;
    let cancelled = false;
    const timerId = window.setTimeout(() => {
      if (cancelled || !holderRef.current) return;
      editor = new EditorJS({
        holder: holderRef.current,
        data: parseDocument(initialContent),
        minHeight: 420,
        placeholder: "내용을 입력하거나 + 버튼으로 블록을 추가하세요.",
        tools: {
          header: { class: Header, toolbox: false, inlineToolbar: true, config: { levels: [1, 2, 3, 4, 5, 6], defaultLevel: 2 } },
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
            config: {
              uploader: { uploadByFile: uploadResponse },
              types: "image/jpeg,image/png,image/webp,image/gif",
            },
          },
          attaches: {
            class: AttachesTool,
            config: { uploader: { uploadByFile: uploadResponse } },
          },
        },
        i18n: {
          messages: {
            toolNames: {
              Text: "텍스트", Heading: "제목", "Unordered List": "글머리 목록",
              "Ordered List": "번호 목록", Checklist: "체크리스트", Quote: "인용",
              Table: "표", Warning: "경고", Code: "코드", Delimiter: "구분선",
              Image: "이미지", Attachment: "파일", Embed: "미디어 삽입",
            },
          },
        },
      });
      editorRef.current = editor;
      editor.isReady.catch(() => onError?.("편집기를 불러오지 못했습니다. 페이지를 새로고침해 주세요."));
    }, 0);

    return () => {
      cancelled = true;
      window.clearTimeout(timerId);
      if (editorRef.current === editor) editorRef.current = null;
      editor?.isReady.then(() => editor.destroy()).catch(() => {});
    };
  }, [editorRef, initialContent, onError]);

  return <div className="editorjs-dashboard" ref={holderRef} />;
}
