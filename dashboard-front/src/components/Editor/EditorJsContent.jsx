function parseDocument(content = "") {
  try {
    const document = JSON.parse(content);
    return Array.isArray(document.blocks) ? document : null;
  } catch {
    return null;
  }
}

const Inline = ({ html = "" }) => <span dangerouslySetInnerHTML={{ __html: html }} />;

function assetUrl(value = "") {
  try {
    const url = new URL(value, window.location.origin);
    if (/^\/blog\/assets\/[0-9a-f-]+\/(?:content|download)\/$/i.test(url.pathname)) {
      return `${url.pathname}${url.search}`;
    }
  } catch {
    // Let the browser handle non-URL values as it did previously.
  }
  return value;
}

function videoEmbedUrl(value = "") {
  try {
    const url = new URL(value);
    if (url.hostname === "youtu.be") return `https://www.youtube.com/embed/${url.pathname.slice(1)}`;
    if (["youtube.com", "www.youtube.com"].includes(url.hostname)) {
      const id = url.searchParams.get("v") || url.pathname.match(/^\/embed\/([^/]+)/)?.[1];
      if (id) return `https://www.youtube.com/embed/${id}`;
    }
    if (["vimeo.com", "www.vimeo.com"].includes(url.hostname)) {
      const id = url.pathname.match(/^\/(\d+)/)?.[1];
      if (id) return `https://player.vimeo.com/video/${id}`;
    }
  } catch { /* invalid URL */ }
  return "";
}

function EditorList({ items = [], style = "unordered" }) {
  const List = style === "ordered" ? "ol" : "ul";
  const checklist = style === "checklist";
  return <List className={checklist ? "editor-checklist" : undefined}>{items.map((item, index) => {
    const value = typeof item === "string" ? { content: item, items: [] } : item;
    return <li className={checklist && value?.meta?.checked ? "checked" : ""} key={index}>{checklist && <span aria-hidden="true">{value?.meta?.checked ? "✓" : "○"}</span>}<Inline html={value?.content} />{value?.items?.length > 0 && <EditorList items={value.items} style={style} />}</li>;
  })}</List>;
}

function EditorBlock({ block }) {
  const data = block.data ?? {};
  if (block.type === "paragraph") return <p><Inline html={data.text} /></p>;
  if (block.type === "header") {
    const level = Math.min(6, Math.max(1, Number(data.level) || 2));
    const Heading = `h${level}`;
    return <Heading><Inline html={data.text} /></Heading>;
  }
  if (block.type === "list") return <EditorList items={data.items} style={data.style} />;
  if (block.type === "quote") return <blockquote><p><Inline html={data.text} /></p>{data.caption && <cite><Inline html={data.caption} /></cite>}</blockquote>;
  if (block.type === "checklist") return <ul className="editor-checklist">{(data.items ?? []).map((item, index) => <li className={item.checked ? "checked" : ""} key={index}><span aria-hidden="true">{item.checked ? "✓" : "○"}</span><Inline html={item.text} /></li>)}</ul>;
  if (block.type === "table") return <div className="editor-table-wrap"><table><tbody>{(data.content ?? []).map((row, rowIndex) => <tr key={rowIndex}>{row.map((cell, cellIndex) => { const Cell = data.withHeadings && rowIndex === 0 ? "th" : "td"; return <Cell key={cellIndex}><Inline html={cell} /></Cell>; })}</tr>)}</tbody></table></div>;
  if (block.type === "warning") return <aside className="editor-warning"><strong><Inline html={data.title} /></strong><p><Inline html={data.message} /></p></aside>;
  if (block.type === "embed") return <figure className="editor-embed"><iframe src={data.embed} title={data.caption?.replace(/<[^>]*>/g, "") || `${data.service || "미디어"} 임베드`} loading="lazy" allowFullScreen />{data.caption && <figcaption><Inline html={data.caption} /></figcaption>}</figure>;
  if (block.type === "video") { const src = videoEmbedUrl(data.url); return src ? <figure className="editor-embed"><iframe src={src} title={data.caption?.replace(/<[^>]*>/g, "") || "영상"} loading="lazy" allowFullScreen />{data.caption && <figcaption><Inline html={data.caption} /></figcaption>}</figure> : null; }
  if (block.type === "linkCard") return <a className="editor-link-card" href={data.url} target="_blank" rel="noopener noreferrer"><strong><Inline html={data.title || data.url} /></strong>{data.description && <span><Inline html={data.description} /></span>}<small>{data.url}</small></a>;
  if (block.type === "code") return <pre><code>{data.code}</code></pre>;
  if (block.type === "delimiter") return <hr />;
  if (block.type === "image") return <figure><img src={assetUrl(data.file?.url)} alt={data.caption?.replace(/<[^>]*>/g, "") || "연구 이미지"} />{data.caption && <figcaption><Inline html={data.caption} /></figcaption>}</figure>;
  if (block.type === "attaches") return <a className="research-attachment" href={assetUrl(data.file?.url)} download><strong>{data.title || data.file?.name || "첨부파일"}</strong><span>다운로드</span></a>;
  return null;
}

export function EditorJsContent({ content = "" }) {
  const document = parseDocument(content);
  if (document) return document.blocks.map((block, index) => <EditorBlock block={block} key={index} />);
  if (/<[a-z][\s\S]*>/i.test(content)) return <div dangerouslySetInnerHTML={{ __html: content }} />;
  return content.split(/\n{2,}/).filter(Boolean).map((text, index) => <p key={index}>{text}</p>);
}

