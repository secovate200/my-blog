function parseDocument(content = "") {
  try {
    const document = JSON.parse(content);
    return Array.isArray(document.blocks) ? document : null;
  } catch {
    return null;
  }
}

const Inline = ({ html = "" }) => <span dangerouslySetInnerHTML={{ __html: html }} />;

function EditorList({ items = [], ordered = false }) {
  const List = ordered ? "ol" : "ul";
  return <List>{items.map((item, index) => {
    const value = typeof item === "string" ? { content: item, items: [] } : item;
    return <li key={index}><Inline html={value?.content} />{value?.items?.length > 0 && <EditorList items={value.items} ordered={ordered} />}</li>;
  })}</List>;
}

function EditorBlock({ block }) {
  const data = block.data ?? {};
  if (block.type === "paragraph") return <p><Inline html={data.text} /></p>;
  if (block.type === "header") {
    const level = Math.min(6, Math.max(2, Number(data.level) || 2));
    const Heading = `h${level}`;
    return <Heading><Inline html={data.text} /></Heading>;
  }
  if (block.type === "list") return <EditorList items={data.items} ordered={data.style === "ordered"} />;
  if (block.type === "quote") return <blockquote><p><Inline html={data.text} /></p>{data.caption && <cite><Inline html={data.caption} /></cite>}</blockquote>;
  if (block.type === "code") return <pre><code>{data.code}</code></pre>;
  if (block.type === "delimiter") return <hr />;
  if (block.type === "image") return <figure><img src={data.file?.url} alt={data.caption?.replace(/<[^>]*>/g, "") || "연구 이미지"} />{data.caption && <figcaption><Inline html={data.caption} /></figcaption>}</figure>;
  if (block.type === "attaches") return <a className="research-attachment" href={data.file?.url} download><strong>{data.title || data.file?.name || "첨부파일"}</strong><span>다운로드</span></a>;
  return null;
}

export function EditorJsContent({ content = "" }) {
  const document = parseDocument(content);
  if (document) return document.blocks.map((block, index) => <EditorBlock block={block} key={index} />);
  if (/<[a-z][\s\S]*>/i.test(content)) return <div dangerouslySetInnerHTML={{ __html: content }} />;
  return content.split(/\n{2,}/).filter(Boolean).map((text, index) => <p key={index}>{text}</p>);
}

