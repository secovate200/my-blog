import { useEffect, useState } from "react";
import { FaArrowLeft, FaPen, FaTrash } from "react-icons/fa6";
import { deletePost, fetchAdminPost } from "../../api";
import { EditorJsContent } from "../../components/Editor/EditorJsContent";
import { WriteContent } from "../../components/Editor/WriteContent";
import { navigateToErrorPage } from "../../utils/errorNavigation";
import "./detail.css";

export function BlogPostContent({ postId, mode = "view", theme, categories, permissions = {} }) {
  const [post, setPost] = useState(null);
  const [message, setMessage] = useState("불러오는 중입니다.");

  useEffect(() => {
    fetchAdminPost(postId).then((item) => { setPost(item); setMessage(""); }).catch((error) => navigateToErrorPage(error, 404));
  }, [postId]);

  if (!post) return <main className="content blog-detail-missing"><h1>{message}</h1><a href="#/blog">게시글 목록</a></main>;
  if (mode === "edit") {
    const category = categories.find((item) => item.name === post.category);
    return <WriteContent key={post.id} theme={theme} categoryOptions={categories} initialCategory={category?.id ?? ""} defaultVisibility={post.visibility ?? "public"} initialPost={post} />;
  }

  const remove = async () => {
    if (!window.confirm(`“${post.title}” 게시글을 삭제할까요?`)) return;
    try { await deletePost(post.id); window.location.hash = "/blog"; } catch (error) { navigateToErrorPage(error); }
  };

  return <main className="content blog-detail-content"><div className="blog-detail-toolbar"><a href="#/blog"><FaArrowLeft /> 게시글 목록</a>{(permissions.changePosts || permissions.deletePosts) && <div>{permissions.changePosts && <a href={`#/blog-edit?id=${encodeURIComponent(post.id)}`}><FaPen /> 수정</a>}{permissions.deletePosts && <button type="button" onClick={remove}><FaTrash /> 삭제</button>}</div>}</div>{message && <p role="status">{message}</p>}<article className="blog-detail-article"><header><span>{post.category}</span><h1>{post.title}</h1><div><span>{post.status === "published" ? "게시됨" : "임시 저장"}</span><time>{new Intl.DateTimeFormat("ko-KR").format(new Date(post.updatedAt))}</time></div></header><div className="blog-detail-body"><EditorJsContent content={post.content} /></div></article></main>;
}

