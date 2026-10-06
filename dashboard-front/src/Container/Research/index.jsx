import { useEffect, useState } from "react";
import { FaLock, FaPenToSquare } from "react-icons/fa6";
import { fetchAdminResearchPosts } from "../../api";
import { ContentHeader } from "../../components/Layout/ContentHeader";
import { navigateToErrorPage } from "../../utils/errorNavigation";
import "./style.css";

export const ResearchContent = ({ categories, onWrite }) => {
  const [selectedCategory, setSelectedCategory] = useState(categories[0]?.id ?? "");
  const [posts, setPosts] = useState([]);
  const [message, setMessage] = useState("");
  useEffect(() => { if (!selectedCategory && categories[0]) setSelectedCategory(categories[0].id); }, [categories, selectedCategory]);
  useEffect(() => { if (!selectedCategory) return; setMessage("불러오는 중입니다."); fetchAdminResearchPosts(selectedCategory).then(({ items }) => { setPosts(items); setMessage(""); }).catch((error) => navigateToErrorPage(error)); }, [selectedCategory]);
  const status = (post) => post.visibility === "private" ? "비공개" : post.status === "published" ? "공개" : "작성 중";
  return <main className="content research-content"><ContentHeader title="연구 관리" /><section className="research-panel"><aside className="research-categories" aria-label="연구 프로젝트"><div className="research-categories--header"><h2>연구 프로젝트</h2></div><div className="research-category-list">{categories.map((category) => <button className={String(selectedCategory) === String(category.id) ? "active" : ""} type="button" onClick={() => setSelectedCategory(category.id)} key={category.id}><span>{category.name}</span><strong>{category.postCount}</strong></button>)}</div></aside><div className="research-posts"><div className="research-posts--header"><div><h2>{categories.find((category) => String(category.id) === String(selectedCategory))?.name || "연구 프로젝트"}</h2><p><FaLock /> 연구 게시글은 기본적으로 비공개로 저장됩니다.</p></div><button type="button" onClick={() => onWrite(selectedCategory)} disabled={!selectedCategory}><FaPenToSquare /> 연구 글 작성</button></div>{message && <p role="status">{message}</p>}<div className="research-table" role="table" aria-label="연구 게시글 목록"><div className="research-row research-row--head" role="row"><span>제목</span><span>상태</span><span>수정일</span></div>{posts.length ? posts.map((post) => <div className="research-row" role="row" key={post.id}><a className="research-title-link" href={`#/research-view?id=${post.id}`}>{post.title}</a><span className="research-status"><FaLock /> {status(post)}</span><span>{new Intl.DateTimeFormat("ko-KR").format(new Date(post.updatedAt))}</span></div>) : !message && <div className="research-empty"><FaLock /><strong>아직 작성된 연구 글이 없습니다.</strong><span>이 프로젝트에서 첫 번째 연구 글을 작성해 보세요.</span></div>}</div></div></section></main>;
};
