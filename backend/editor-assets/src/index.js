import AttachesTool from "@editorjs/attaches";
import CodeTool from "@editorjs/code";
import Delimiter from "@editorjs/delimiter";
import EditorJS from "@editorjs/editorjs";
import Header from "@editorjs/header";
import ImageTool from "@editorjs/image";
import EditorjsList from "@editorjs/list";
import Quote from "@editorjs/quote";

function csrfToken() {
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith("csrftoken="))
    ?.split("=")[1];
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
  return result;
}

function initialData(value) {
  try {
    const data = JSON.parse(value);
    if (Array.isArray(data.blocks)) {
      data.blocks = data.blocks.map((block) =>
        block.type === "quote"
          ? {
              ...block,
              data: {
                ...block.data,
                text: trimEmptyLines(block.data.text),
                caption: trimEmptyLines(block.data.caption),
              },
            }
          : block,
      );
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

  const editor = new EditorJS({
    holder,
    data: initialData(textarea.value),
    placeholder: "내용을 입력하거나 + 버튼으로 블록을 추가하세요.",
    tools: {
      header: {
        class: Header,
        config: { levels: [1, 2, 3, 4, 5, 6], defaultLevel: 2 },
      },
      list: { class: EditorjsList, inlineToolbar: true },
      quote: { class: Quote, inlineToolbar: true },
      code: CodeTool,
      delimiter: Delimiter,
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
