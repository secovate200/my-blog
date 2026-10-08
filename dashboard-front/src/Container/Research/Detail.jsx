import { useEffect, useRef, useState } from "react";
import { FaArrowLeft, FaDownload, FaLock, FaPen } from "react-icons/fa6";
import { fetchAdminResearchPost } from "../../api";
import { EditorJsContent } from "../../components/Editor/EditorJsContent";
import { WriteContent } from "../../components/Editor/WriteContent";
import { navigateToErrorPage } from "../../utils/errorNavigation";
import "./detail.css";

export const ResearchDetailContent = ({ postId, mode = "view", theme, categories = [] }) => {
  const articleRef = useRef(null);
  const [post, setPost] = useState(null);
  const [message, setMessage] = useState("불러오는 중입니다.");
  const [downloading, setDownloading] = useState(false);
  useEffect(() => { fetchAdminResearchPost(postId).then((item) => { setPost(item); setMessage(""); }).catch((error) => navigateToErrorPage(error, 404)); }, [postId]);
  const downloadPdf = async () => { setDownloading(true); let container; try { const { default: html2pdf } = await import("html2pdf.js"); const source = articleRef.current.cloneNode(true); source.removeAttribute("id"); source.classList.add("pdf-export-mode"); container = document.createElement("div"); container.className = "research-pdf-export-container"; container.appendChild(source); document.body.appendChild(container); await html2pdf().set({ margin: 0, filename: `${post.title}.pdf`, image: { type: "jpeg", quality: 0.98 }, html2canvas: { scale: 2, useCORS: true, backgroundColor: "#ffffff" }, jsPDF: { unit: "mm", format: "a4", orientation: "portrait" }, pagebreak: { mode: ["avoid-all", "css", "legacy"] } }).from(source).save(); } finally { container?.remove(); setDownloading(false); } };
  if (!post) return <main className="content research-detail-missing"><h1>{message}</h1><a href="#/research">연구 목록으로 돌아가기</a></main>;
  if (mode === "edit") {
    const projectId = post.projectId ?? categories.find((item) => item.name === post.projectName)?.id ?? "";
    return <WriteContent key={post.id} theme={theme} categoryOptions={categories} initialCategory={projectId} defaultVisibility={post.visibility ?? "private"} titlePlaceholder="연구 게시글 제목" postType="research" initialPost={post} />;
  }
  const state = post.visibility === "private" ? "비공개" : post.status === "published" ? "공개" : "작성 중";
  return <main className="content research-detail-content"><div className="research-detail-toolbar"><a href="#/research"><FaArrowLeft /> 연구 목록</a><div className="research-detail-actions"><a href={`#/research-edit?id=${encodeURIComponent(post.id)}`}><FaPen /> 수정</a><button type="button" onClick={downloadPdf} disabled={downloading}><FaDownload /> {downloading ? "PDF 생성 중..." : "PDF 다운로드"}</button></div></div><article id="research-pdf-source" className="research-article" ref={articleRef}><div className="research-pdf-masthead"><strong>SECOVATE200</strong><span>RESEARCH REPORT</span></div><header><div className="research-article--meta"><span>{post.projectName}</span><span><FaLock /> {state}</span></div><h1>{post.title}</h1><time>{new Intl.DateTimeFormat("ko-KR").format(new Date(post.updatedAt))}</time></header><dl className="research-pdf-document-info"><div><dt>문서 분류</dt><dd>보안 연구 보고서</dd></div><div><dt>연구 프로젝트</dt><dd>{post.projectName}</dd></div><div><dt>공개 상태</dt><dd>{state}</dd></div><div><dt>최종 수정일</dt><dd>{new Intl.DateTimeFormat("ko-KR").format(new Date(post.updatedAt))}</dd></div></dl><div className="research-article--body"><EditorJsContent content={post.content} /></div><footer className="research-pdf-footer"><span>SECOVATE200 RESEARCH ARCHIVE</span><span>{post.visibility === "private" ? "CONFIDENTIAL" : "PUBLIC"}</span></footer></article></main>;
};
