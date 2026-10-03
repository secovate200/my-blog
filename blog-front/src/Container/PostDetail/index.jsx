import { useEffect, useState } from "react";
import { FiArrowLeft, FiCalendar, FiTag } from "react-icons/fi";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { getPost } from "../../api/post";
import { getProjectPost } from "../../api/project";
import Card from "../../Components/UI/Card";
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

function formatDate(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("ko-KR", { year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date(value));
}

export function PostTableOfContents({ postId, projectId = null }) {
  const { post } = usePost(postId, projectId);
  if (!post) return null;
  return (
    <nav className="postTableOfContents" aria-label="목차"><strong>목차</strong><ol>
      {createPostSections(post.content).map((section) => (
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
        <div className="postDetailBody">
          {createPostSections(post.content).map((section) => (
            <section id={section.id} className="postSection" key={section.id}>
              <h2>{section.title}</h2><p>{section.content}</p>
            </section>
          ))}
        </div>
      </article>
    </Card></div>
  );
}

export function ProjectPostDetail() {
  return <PostDetail isProjectPost />;
}

export default PostDetail;
