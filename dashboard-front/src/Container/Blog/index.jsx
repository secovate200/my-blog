import { useEffect, useState } from "react";
import { ContentHeader } from "../../components/Layout/ContentHeader";
import TableList from "../../components/UI/TableList";
import { fetchAdminPosts } from "../../api";
import { navigateToErrorPage } from "../../utils/errorNavigation";
import "../Dashboard/style.css";

const POSTS_PER_PAGE = 8;

export const BlogContent = ({ theme, onToggleTheme }) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [posts, setPosts] = useState([]);
  const [message, setMessage] = useState("불러오는 중입니다.");
  useEffect(() => { fetchAdminPosts().then(({ items }) => { setPosts(items.map((post) => ({ ...post, category: post.category, status: post.status === "published" ? "Published" : post.status === "review" ? "Review" : "Draft", date: new Intl.DateTimeFormat("ko-KR").format(new Date(post.updatedAt)) }))); setMessage(""); }).catch((error) => navigateToErrorPage(error)); }, []);
  const totalPages = Math.max(1, Math.ceil(posts.length / POSTS_PER_PAGE));
  const start = (currentPage - 1) * POSTS_PER_PAGE;
  const visiblePosts = posts.slice(start, start + POSTS_PER_PAGE).map((post, index) => ({
    ...post,
    displayId: start + index + 1,
  }));

  useEffect(() => {
    document.querySelector(".table-list--scroll")?.scrollTo({ left: 0 });
  }, [currentPage]);

  const goToPage = (page) => {
    setCurrentPage(Math.min(Math.max(page, 1), totalPages));
  };

  const pagination = (
    <nav className="pagination" aria-label="블로그 페이지 이동">
      <button
        type="button"
        className="pagination--button pagination--control"
        onClick={() => goToPage(currentPage - 1)}
        disabled={currentPage === 1}
      >
        이전
      </button>
      <div className="pagination--pages">
        {Array.from({ length: totalPages }, (_, index) => index + 1).map((page) => (
          <button
            type="button"
            className={`pagination--button ${page === currentPage ? "pagination--active" : ""}`}
            aria-current={page === currentPage ? "page" : undefined}
            onClick={() => goToPage(page)}
            key={page}
          >
            {page}
          </button>
        ))}
      </div>
      <button
        type="button"
        className="pagination--button pagination--control"
        onClick={() => goToPage(currentPage + 1)}
        disabled={currentPage === totalPages}
      >
        다음
      </button>
    </nav>
  );

  return (
    <main className="content blog-content">
      <ContentHeader title="블로그" theme={theme} onToggleTheme={onToggleTheme} />
      {message && <p role="status">{message}</p>}
      <TableList
        title="전체 게시글"
        items={visiblePosts}
        showViewAll={false}
        minimumRows={POSTS_PER_PAGE}
        linkTitles
        labels={["번호", "제목", "카테고리", "상태", "수정일"]}
        footer={pagination}
      />
    </main>
  );
};
