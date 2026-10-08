import { useEffect, useMemo, useState } from "react";
import { FiArrowLeft, FiCalendar, FiTag } from "react-icons/fi";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { getPost } from "../../api/post";
import { getProjectPost } from "../../api/project";
import Card from "../../Components/UI/Card";
import { parseEditorContent } from "../../utils/content";
import "./style.css";

const SECTION_TITLES = ["개요", "핵심 내용", "적용 방법", "점검 체크리스트"];
const postCache = new Map();
const pendingPosts = new Map();

function loadPost(cacheKey, requestPost) {
  if (postCache.has(cacheKey)) return Promise.resolve(postCache.get(cacheKey));
  if (pendingPosts.has(cacheKey)) return pendingPosts.get(cacheKey);
  const request = requestPost().then((post) => {
    postCache.set(cacheKey, post);
    pendingPosts.delete(cacheKey);
    return post;
  }).catch((error) => {
    pendingPosts.delete(cacheKey);
    throw error;
  });
  pendingPosts.set(cacheKey, request);
  return request;
}

function usePost(postId, projectId = null) {
  const cacheKey = projectId
    ? `project:${projectId}:post:${postId}`
    : `post:${postId}`;
  const [result, setResult] = useState(() => ({
    cacheKey,
    post: postCache.get(cacheKey) ?? null,
    isLoading: !postCache.has(cacheKey),
    error: "",
  }));

  useEffect(() => {
    let active = true;
    const requestPost = projectId
      ? () => getProjectPost(projectId, postId)
      : () => getPost(postId);
    loadPost(cacheKey, requestPost)
      .then((data) => active && setResult({ cacheKey, post: data, isLoading: false, error: "" }))
      .catch(() => active && setResult({
        cacheKey,
        post: null,
        isLoading: false,
        error: "게시글을 찾을 수 없습니다.",
      }));
    return () => { active = false; };
  }, [cacheKey, postId, projectId]);

  if (result.cacheKey !== cacheKey) {
    return {
      post: postCache.get(cacheKey) ?? null,
      isLoading: !postCache.has(cacheKey),
      error: "",
    };
  }
  return result;
}

function createPostSections(content = "") {
  return content.split(/(?<=[.!?。])\s+/).filter(Boolean).reduce((sections, sentence, index) => {
    const sectionIndex = Math.floor(index / 3);
    if (!sections[sectionIndex]) {
      sections[sectionIndex] = {
        id: `section-${sectionIndex + 1}`,
        title: SECTION_TITLES[sectionIndex] ?? `추가 내용 ${sectionIndex + 1}`,
        content: sentence,
      };
    } else sections[sectionIndex].content += ` ${sentence}`;
    return sections;
  }, []);
}

function isRichContent(content = "") {
  return /<(?:p|h[2-4]|ul|ol|li|blockquote|pre|code|hr|br)\b/i.test(content);
}

function prepareRichContent(content = "") {
  const editorData = parseEditorContent(content);
  if (editorData) {
    const headings = editorData.blocks
      .filter((block) => block.type === "header" && Number(block.data?.level) <= 3)
      .map((block, index) => ({
        id: `section-${index + 1}`,
        title: block.data.text.replace(/<[^>]*>/g, "").trim() || `섹션 ${index + 1}`,
      }));
    return { blocks: editorData.blocks, headings };
  }
  if (!isRichContent(content)) return null;

  const document = new DOMParser().parseFromString(content, "text/html");
  const headings = Array.from(document.body.querySelectorAll("h1, h2, h3")).map(
    (heading, index) => {
      const id = `section-${index + 1}`;
      heading.id = id;
      return { id, title: heading.textContent?.trim() || `섹션 ${index + 1}` };
    },
  );

  return { headings, html: document.body.innerHTML };
}

function InlineContent({ html }) {
  return <span dangerouslySetInnerHTML={{ __html: html }} />;
}

function trimEmptyLines(html = "") {
  return html.replace(/^(?:\s*<br\s*\/?>(?:\s*))+|(?:(?:\s*)<br\s*\/?>\s*)+$/gi, "");
}

function EditorList({ items = [], style = "unordered" }) {
  const ListTag = style === "ordered" ? "ol" : "ul";
  const checklist = style === "checklist";
  return (
    <ListTag className={checklist ? "postChecklist" : undefined}>
      {items.map((item, index) => {
        const data = typeof item === "string" ? { content: item, items: [] } : item;
        return (
          <li className={checklist && data.meta?.checked ? "checked" : ""} key={index}>
            {checklist && <span aria-hidden="true">{data.meta?.checked ? "✓" : "○"}</span>}
            <InlineContent html={data.content ?? ""} />
            {data.items?.length > 0 && <EditorList items={data.items} style={style} />}
          </li>
        );
      })}
    </ListTag>
  );
}

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

function EditorBlocks({ blocks }) {
  let headingIndex = 0;
  return blocks.map((block, index) => {
    const { data = {} } = block;
    if (block.type === "header") {
      headingIndex += 1;
      const HeadingTag = `h${data.level ?? 2}`;
      return <HeadingTag id={`section-${headingIndex}`} key={index}><InlineContent html={data.text} /></HeadingTag>;
    }
    if (block.type === "paragraph") return <p key={index}><InlineContent html={data.text} /></p>;
    if (block.type === "list") return <EditorList items={data.items} style={data.style} key={index} />;
    if (block.type === "quote") {
      const text = trimEmptyLines(data.text);
      const caption = trimEmptyLines(data.caption);
      return (
        <blockquote key={index}>
          <p><InlineContent html={text} /></p>
          {caption && <cite><InlineContent html={caption} /></cite>}
        </blockquote>
      );
    }
    if (block.type === "checklist") return (
      <ul className="postChecklist" key={index}>{(data.items ?? []).map((item, itemIndex) => (
        <li className={item.checked ? "checked" : ""} key={itemIndex}><span aria-hidden="true">{item.checked ? "✓" : "○"}</span><InlineContent html={item.text} /></li>
      ))}</ul>
    );
    if (block.type === "table") return (
      <div className="postTableWrap" key={index}><table><tbody>{(data.content ?? []).map((row, rowIndex) => (
        <tr key={rowIndex}>{row.map((cell, cellIndex) => { const Cell = data.withHeadings && rowIndex === 0 ? "th" : "td"; return <Cell key={cellIndex}><InlineContent html={cell} /></Cell>; })}</tr>
      ))}</tbody></table></div>
    );
    if (block.type === "warning") return <aside className="postWarning" key={index}><strong><InlineContent html={data.title} /></strong><p><InlineContent html={data.message} /></p></aside>;
    if (block.type === "embed") return <figure className="postEmbed" key={index}><iframe src={data.embed} title={data.caption?.replace(/<[^>]*>/g, "") || `${data.service || "미디어"} 임베드`} loading="lazy" allowFullScreen />{data.caption && <figcaption><InlineContent html={data.caption} /></figcaption>}</figure>;
    if (block.type === "video") { const src = videoEmbedUrl(data.url); return src ? <figure className="postEmbed" key={index}><iframe src={src} title={data.caption?.replace(/<[^>]*>/g, "") || "영상"} loading="lazy" allowFullScreen />{data.caption && <figcaption><InlineContent html={data.caption} /></figcaption>}</figure> : null; }
    if (block.type === "linkCard") return <a className="postLinkCard" href={data.url} target="_blank" rel="noopener noreferrer" key={index}><strong><InlineContent html={data.title || data.url} /></strong>{data.description && <span><InlineContent html={data.description} /></span>}<small>{data.url}</small></a>;
    if (block.type === "code") return <pre key={index}><code>{data.code}</code></pre>;
    if (block.type === "delimiter") return <hr key={index} />;
    if (block.type === "image") return (
      <figure className={`postImage${data.withBorder ? " withBorder" : ""}${data.withBackground ? " withBackground" : ""}`} key={index}>
        <img src={assetUrl(data.file?.url)} alt={data.caption?.replace(/<[^>]*>/g, "") || "게시글 이미지"} loading="lazy" />
        {data.caption && <figcaption><InlineContent html={data.caption} /></figcaption>}
      </figure>
    );
    if (block.type === "attaches") return (
      <a className="postAttachment" href={assetUrl(data.file?.url)} download key={index}>
        <span className="postAttachmentExtension">{data.file?.extension || "FILE"}</span>
        <span>
          <strong>{data.title || data.file?.name || "첨부파일"}</strong>
          <small>{formatFileSize(data.file?.size)}</small>
        </span>
        <span aria-hidden="true">↓</span>
      </a>
    );
    return null;
  });
}

function formatFileSize(size = 0) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("ko-KR", { year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date(value));
}

export function PostTableOfContents({ postId, projectId = null }) {
  const { post } = usePost(postId, projectId);
  const richContent = useMemo(
    () => prepareRichContent(post?.content),
    [post?.content],
  );
  if (!post) return null;
  const sections = richContent?.headings ?? createPostSections(post.content);
  if (sections.length === 0) return null;
  return (
    <nav className="postTableOfContents" aria-label="목차"><strong>목차</strong><ol>
      {sections.map((section) => (
        <li key={section.id}><a href={`#${section.id}`}>{section.title}</a></li>
      ))}
    </ol></nav>
  );
}

function PostDetail({ isProjectPost = false }) {
  const { projectId, postId } = useParams();
  const [searchParams] = useSearchParams();
  const selectedTag = searchParams.get("tag") ?? "";
  const { post, isLoading, error } = usePost(
    postId,
    isProjectPost ? projectId : null,
  );
  const listUrl = isProjectPost
    ? `/project?project=${projectId}${
        selectedTag ? `&tag=${encodeURIComponent(selectedTag)}` : ""
      }`
    : "/";
  const listLabel = isProjectPost ? "프로젝트 글 목록" : "게시글 목록";
  const richContent = useMemo(
    () => prepareRichContent(post?.content),
    [post?.content],
  );

  if (isLoading) return <Card><section className="postNotFound"><p>게시글을 불러오는 중입니다.</p></section></Card>;
  if (error || !post) return (
    <Card><section className="postNotFound"><span>404</span><h1>{error}</h1>
      <Link to={listUrl}><FiArrowLeft aria-hidden="true" />{listLabel}</Link></section></Card>
  );

  return (
    <div className="postDetailLayout"><Card>
      <article className="postDetail" aria-labelledby="post-detail-title">
        <Link className="postBackLink" to={listUrl}><FiArrowLeft aria-hidden="true" />{listLabel}</Link>
        <header className="postDetailHeader">
          <div className="postDetailMeta">
            {isProjectPost ? (
              <Link to={listUrl}>{post.project_title}</Link>
            ) : (
              <Link to={`/?category=${encodeURIComponent(post.category)}`}>{post.category}</Link>
            )}
            <time dateTime={post.created_at}><FiCalendar aria-hidden="true" />{formatDate(post.created_at)}</time>
          </div>
          <h1 id="post-detail-title">{post.title}</h1>
          {post.tags.length > 0 && (
            <div className="postDetailTags"><FiTag aria-hidden="true" />
              {post.tags.map((tag) => (
                isProjectPost
                  ? <span key={tag}>#{tag}</span>
                  : <Link to={`/?tag=${encodeURIComponent(tag)}`} key={tag}>#{tag}</Link>
              ))}
            </div>
          )}
        </header>
        {richContent ? (
          richContent.blocks ? (
            <div className="postDetailBody postRichContent">
              <EditorBlocks blocks={richContent.blocks} />
            </div>
          ) : (
            <div
              className="postDetailBody postRichContent"
              dangerouslySetInnerHTML={{ __html: richContent.html }}
            />
          )
        ) : (
          <div className="postDetailBody">
            {createPostSections(post.content).map((section) => (
              <section id={section.id} className="postSection" key={section.id}>
                <h2>{section.title}</h2><p>{section.content}</p>
              </section>
            ))}
          </div>
        )}
      </article>
    </Card></div>
  );
}

export function ProjectPostDetail() {
  return <PostDetail isProjectPost />;
}

export default PostDetail;
