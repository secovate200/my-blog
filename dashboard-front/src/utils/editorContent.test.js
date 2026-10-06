import assert from "node:assert/strict";
import test from "node:test";
import { blockNoteToEditorJs, serializeForBlog } from "./editorContent.js";

test("DB와 블로그 렌더러가 사용하는 Editor.js 문서를 만든다", () => {
  const content = blockNoteToEditorJs([
    { type: "heading", props: { level: 2 }, content: [{ type: "text", text: "제목", styles: { bold: true } }] },
    { type: "paragraph", content: [{ type: "text", text: "본문 <테스트>", styles: {} }] },
    { type: "bulletListItem", content: [{ type: "text", text: "첫째", styles: {} }], children: [] },
    { type: "bulletListItem", content: [{ type: "text", text: "둘째", styles: {} }], children: [] },
  ], 1791042460072);

  assert.equal(content.version, "2.31.7");
  assert.deepEqual(content.blocks[0], { type: "header", data: { text: "<strong>제목</strong>", level: 2 } });
  assert.equal(content.blocks[1].data.text, "본문 &lt;테스트&gt;");
  assert.equal(content.blocks[2].type, "list");
  assert.equal(content.blocks[2].data.items.length, 2);
  assert.doesNotThrow(() => JSON.parse(serializeForBlog([], 1)));
});

test("DB에 저장된 이미지와 첨부파일 URL 형식을 보존한다", () => {
  const imageUrl = "/blog/assets/8915e3fa-b4ff-4a24-8c10-0e1f3f0b9da1/content/";
  const fileUrl = "/blog/assets/3ab09366-c852-44be-8aab-a463433ac9d7/download/";
  const { blocks } = blockNoteToEditorJs([
    { type: "image", props: { url: imageUrl, caption: "화면" } },
    { type: "file", props: { url: fileUrl, name: "report.txt", caption: "보고서" } },
  ]);

  assert.equal(blocks[0].type, "image");
  assert.equal(blocks[0].data.file.url, imageUrl);
  assert.equal(blocks[1].type, "attaches");
  assert.deepEqual(blocks[1].data.file, { url: fileUrl, name: "report.txt", size: 0, extension: "txt" });
});

test("지원하지 않는 BlockNote 블록은 DB 문서에서 제외한다", () => {
  const { blocks } = blockNoteToEditorJs([
    { type: "audio", props: { url: "/audio.mp3" } },
    { type: "paragraph", content: [{ type: "text", text: "유효", styles: {} }] },
  ]);
  assert.deepEqual(blocks, [{ type: "paragraph", data: { text: "유효" } }]);
});

test("코드 블록은 HTML 문자를 원문 그대로 저장한다", () => {
  const { blocks } = blockNoteToEditorJs([
    { type: "codeBlock", content: [{ type: "text", text: "if (a < b) {\n  return true;\n}", styles: {} }] },
  ]);
  assert.equal(blocks[0].data.code, "if (a < b) {\n  return true;\n}");
});

