import { useEffect, useState } from "react";
import { FiArrowLeft, FiCalendar, FiTag } from "react-icons/fi";
import { Link, useParams } from "react-router-dom";
import { getPost } from "../../api/post";
import Card from "../../Components/UI/Card";
import "./style.css";

const SECTION_TITLES = ["개요", "핵심 내용", "적용 방법", "점검 체크리스트"];
const postCache = new Map();
const pendingPosts = new Map();

function loadPost(postId) {
  if (postCache.has(postId)) return Promise.resolve(postCache.get(postId));
  if (pendingPosts.has(postId)) return pendingPosts.get(postId);
  const request = getPost(postId).then((post) => {
    postCache.set(postId, post);
    pendingPosts.delete(postId);
    return post;
  }).catch((error) => {
    pendingPosts.delete(postId);
    throw error;
  });
  pendingPosts.set(postId, request);
  return request;
}

function usePost(postId) {
  const [result, setResult] = useState(() => ({
    postId,
    post: postCache.get(postId) ?? null,
    isLoading: !postCache.has(postId),
    error: "",
  }));

  useEffect(() => {
    let active = true;
    loadPost(postId)
      .then((data) => active && setResult({ postId, post: data, isLoading: false, error: "" }))
      .catch(() => active && setResult({
        postId,
        post: null,
        isLoading: false,
        error: "게시글을 찾을 수 없습니다.",
      }));
    return () => { active = false; };
  }, [postId]);

  if (result.postId !== postId) {
    return {
      post: postCache.get(postId) ?? null,
      isLoading: !postCache.has(postId),
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

export function PostTableOfContents({ postId }) {
  const { post } = usePost(postId);
  if (!post) return null;
  return (
    <nav className="postTableOfContents" aria-label="목차"><strong>목차</strong><ol>
      {createPostSections(post.content).map((section) => (
        <li key={section.id}><a href={`#${section.id}`}>{section.title}</a></li>
      ))}
    </ol></nav>
  );
}

function PostDetail() {
  const { postId } = useParams();
  const { post, isLoading, error } = usePost(postId);

  if (isLoading) return <Card><section className="postNotFound"><p>게시글을 불러오는 중입니다.</p></section></Card>;
  if (error || !post) return (
    <Card><section className="postNotFound"><span>404</span><h1>{error}</h1>
      <Link to="/"><FiArrowLeft aria-hidden="true" />게시글 목록</Link></section></Card>
  );

  return (
    <div className="postDetailLayout"><Card>
      <article className="postDetail" aria-labelledby="post-detail-title">
        <Link className="postBackLink" to="/"><FiArrowLeft aria-hidden="true" />게시글 목록</Link>
        <header className="postDetailHeader">
          <div className="postDetailMeta">
            <Link to={`/?category=${encodeURIComponent(post.category)}`}>{post.category}</Link>
            <time dateTime={post.created_at}><FiCalendar aria-hidden="true" />{formatDate(post.created_at)}</time>
          </div>
          <h1 id="post-detail-title">{post.title}</h1>
          <div className="postDetailTags"><FiTag aria-hidden="true" />
            {post.tags.map((tag) => <Link to={`/?tag=${encodeURIComponent(tag)}`} key={tag}>#{tag}</Link>)}
          </div>
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

export default PostDetail;
