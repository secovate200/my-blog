import { useEffect, useRef } from "react";
import EditorJS from "@editorjs/editorjs";
import Header from "@editorjs/header";
import EditorjsList from "@editorjs/list";
import Quote from "@editorjs/quote";
import CodeTool from "@editorjs/code";
import ImageTool from "@editorjs/image";
import AttachesTool from "@editorjs/attaches";
import Delimiter from "@editorjs/delimiter";
import { uploadMedia } from "../../api";

const EMPTY_DOCUMENT = { blocks: [] };

function parseDocument(content) {
  if (!content) return EMPTY_DOCUMENT;
  try {
    const document = typeof content === "string" ? JSON.parse(content) : content;
    return Array.isArray(document?.blocks) ? document : EMPTY_DOCUMENT;
  } catch {
    return {
      blocks: [{ type: "paragraph", data: { text: String(content) } }],
    };
  }
}

const uploadResponse = async (file) => ({
  success: 1,
  file: await uploadMedia(file),
});

export default function EditorJsEditor({ initialContent = "", editorRef }) {
  const holderRef = useRef(null);

  useEffect(() => {
    if (!holderRef.current) return undefined;

    const editor = new EditorJS({
      holder: holderRef.current,
      data: parseDocument(initialContent),
      minHeight: 420,
      placeholder: "내용을 입력하거나 + 버튼으로 블록을 추가하세요.",
      tools: {
        header: { class: Header, inlineToolbar: true, config: { levels: [2, 3, 4], defaultLevel: 2 } },
        list: { class: EditorjsList, inlineToolbar: true },
        quote: { class: Quote, inlineToolbar: true },
        code: CodeTool,
        delimiter: Delimiter,
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
    });
    editorRef.current = editor;

    return () => {
      if (editorRef.current === editor) editorRef.current = null;
      editor.isReady.then(() => editor.destroy()).catch(() => {});
    };
  }, [editorRef, initialContent]);

  return <div className="editorjs-dashboard" ref={holderRef} />;
}
