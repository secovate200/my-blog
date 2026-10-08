import React, { useEffect, useState } from "react";
import { ContentHeader } from "../../components/Layout/ContentHeader";
import { Card } from "../../components/UI/Card";
import TableList from "../../components/UI/TableList";
import { fetchDashboardSummary } from "../../api";
import { navigateToErrorPage } from "../../utils/errorNavigation";
import "./style.css";
export const Content = ({ theme, onToggleTheme, onViewAll, onViewCategories, onViewPosts, onViewResearch }) => {
  const [summary, setSummary] = useState({ posts: [], postCount: 0, categories: 0, projects: 0 });
  useEffect(() => {
    fetchDashboardSummary().then((data) => {
      const posts = data.recentPosts.map((post, index) => ({ ...post, displayId: index + 1, status: post.status === "published" ? "Published" : "Draft", date: new Intl.DateTimeFormat("ko-KR").format(new Date(post.updatedAt)) }));
      setSummary({ posts, postCount: data.counts.posts, categories: data.counts.categories, researchPosts: data.counts.researchPosts });
    }).catch((error) => navigateToErrorPage(error));
  }, []);
  return (
    <div className="content">
      <ContentHeader theme={theme} onToggleTheme={onToggleTheme} />
      <Card
        counts={{ category: summary.categories, post: summary.postCount, research: summary.researchPosts }}
        onCategoryClick={onViewCategories}
        onPostClick={onViewPosts}
        onResearchClick={onViewResearch}
      />
      <TableList
        items={summary.posts}
        title="최근 게시글"
        labels={["번호", "제목", "카테고리", "상태", "수정일"]}
        viewAllLabel="전체 보기"
        linkTitles
        onViewAll={onViewAll}
      />
    </div>
  );
};
