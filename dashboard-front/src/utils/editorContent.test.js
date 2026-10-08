import assert from "node:assert/strict";
import test from "node:test";
import { editorJsToPlainText } from "./editorContent.js";

test("Editor.js 문서에서 요약용 텍스트를 만든다", () => {
  const text = editorJsToPlainText({
    blocks: [
      { type: "header", data: { text: "<b>제목</b>", level: 2 } },
      { type: "paragraph", data: { text: "본문 &lt;테스트&gt;" } },
      {
        type: "list",
        data: {
          items: [
            { content: "첫째", items: [{ content: "하위 항목", items: [] }] },
            { content: "둘째", items: [] },
          ],
        },
      },
      { type: "code", data: { code: "const ready = true;" } },
    ],
  });

  assert.equal(
    text,
    "제목\n\n본문 <테스트>\n\n첫째\n\n하위 항목\n\n둘째\n\nconst ready = true;",
  );
});

test("이미지 설명과 첨부파일 이름을 요약에 포함한다", () => {
  const text = editorJsToPlainText({
    blocks: [
      { type: "image", data: { caption: "구성 화면" } },
      { type: "attaches", data: { file: { name: "report.pdf" } } },
    ],
  });

  assert.equal(text, "구성 화면\n\nreport.pdf");
});
