import { FaFolderOpen } from "react-icons/fa6";
import { ContentHeader } from "../../components/Layout/ContentHeader";
import { useEffect, useState } from "react";
import { fetchAdminCategories } from "../../api";
import { navigateToErrorPage } from "../../utils/errorNavigation";
import "./style.css";

export const CategoriesContent = ({ showDrafts = false }) => {
  const [categories, setCategories] = useState([]);
  const [message, setMessage] = useState("불러오는 중입니다.");
  useEffect(() => { fetchAdminCategories().then(({ items }) => { setCategories(items); setMessage(""); }).catch((error) => navigateToErrorPage(error)); }, []);

  return (
    <main className="content categories-content">
      <ContentHeader title="카테고리" />
      <section className="categories-panel" aria-labelledby="category-list-title">
        <div className="categories-heading">
          <div><h2 id="category-list-title">카테고리 목록</h2><p>게시글을 주제별로 분류하고 현황을 확인합니다.</p></div>
          <strong>{categories.length}개</strong>
        </div>
        {message && <p role="status">{message}</p>}
        <div className="category-grid">
          {categories.map((category) => (
            <article className="category-item" key={category.name}>
              <div className="category-item--icon" aria-hidden="true"><FaFolderOpen /></div>
              <div className="category-item--body"><h3>{category.name}</h3><p>전체 게시글 <strong>{category.total}</strong>개</p></div>
              <dl className="category-item--stats">
                <div><dt>공개</dt><dd>{category.published}</dd></div>
                {showDrafts && <div><dt>작성 중</dt><dd>{category.draft}</dd></div>}
              </dl>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
};
