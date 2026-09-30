import { useState } from "react";
import { FiCalendar, FiTag } from "react-icons/fi";
import { useNavigate, useSearchParams } from "react-router-dom";
import "./style.css";

const POSTS_PER_PAGE = 10;
const PREVIEW_LENGTH = 250;

// Shared with the category archive so its counts always match the home feed.
// oxlint-disable-next-line react/only-export-components
export const POSTS = [
  [
    "Web Security",
    "웹 애플리케이션에서 놓치기 쉬운 접근 제어 취약점",
    "Lorem ipsum dolor, sit amet consectetur adipisicing elit. Tenetur, eius exercitationem, non, neque repudiandae ullam perferendis deleniti numquam quidem quasi consequatur pariatur earum vitae sunt similique doloribus impedit nemo nostrum! Dolore, asperiores id facilis, temporibus accusantium at sunt fugiat quo soluta veritatis cupiditate consequuntur error laborum quisquam tenetur optio earum tempora corrupti voluptas. Et illum nulla vero reprehenderit perferendis voluptatum est quo unde aut architecto distinctio numquam, inventore exercitationem in. Minima facilis sit possimus dolore? Asperiores, autem placeat dolorum fuga reiciendis architecto! Quis incidunt facere excepturi dignissimos veritatis nihil modi vel nesciunt maxime, unde illum et delectus recusandae minima debitis adipisci expedita repellendus voluptatibus dolor, tenetur non ipsum exercitationem! Dolore sapiente, voluptate quae quos, recusandae iusto culpa rem quasi totam facilis eaque blanditiis odio. Repellendus mollitia eaque magnam harum, explicabo culpa veritatis non minus libero perferendis iure neque tenetur eos?",
    "2026. 09. 29",
    ["Access Control", "OWASP"],
  ],
  [
    "Bug Bounty",
    "버그바운티 리포트의 재현 가능성을 높이는 방법",
    "담당자가 취약점을 빠르게 이해할 수 있도록 재현 단계와 영향도, 증거 자료를 구성하는 방법을 살펴봅니다.",
    "2026. 09. 24",
    ["Report", "Methodology"],
  ],
  [
    "Development",
    "React 블로그에 다크 모드를 적용하며 배운 것들",
    "CSS 변수로 색상 체계를 분리하고 사용자 경험을 해치지 않으면서 테마를 전환하는 과정을 기록합니다.",
    "2026. 09. 18",
    ["React", "CSS"],
  ],
  [
    "Web Security",
    "CORS 설정을 점검할 때 확인해야 할 항목",
    "Origin 검증과 자격 증명 허용 설정에서 자주 발생하는 실수를 예제와 함께 정리했습니다.",
    "2026. 09. 12",
    ["CORS", "Browser"],
  ],
  [
    "Bug Bounty",
    "효율적인 서브도메인 정찰 워크플로",
    "수집한 서브도메인의 중복을 제거하고 실제 서비스 중인 대상을 선별하는 기본 흐름을 소개합니다.",
    "2026. 09. 07",
    ["Recon", "Automation"],
  ],
  [
    "Development",
    "Vite 환경에서 React 프로젝트 구조 잡기",
    "작은 프로젝트가 커져도 관리하기 쉽도록 컴포넌트와 컨테이너, 공통 스타일을 나누는 기준을 기록합니다.",
    "2026. 08. 30",
    ["Vite", "React"],
  ],
  [
    "Web Security",
    "JWT를 사용할 때 피해야 할 보안 실수",
    "서명 검증과 만료 시간, 토큰 저장 위치 등 JWT 구현 과정에서 확인해야 할 핵심 항목을 살펴봅니다.",
    "2026. 08. 22",
    ["JWT", "Authentication"],
  ],
  [
    "Lab",
    "로컬 보안 테스트 환경을 구성하는 방법",
    "격리된 환경에서 웹 취약점을 안전하게 실습하기 위한 도구와 네트워크 구성 과정을 정리합니다.",
    "2026. 08. 15",
    ["Lab", "Docker"],
  ],
  [
    "Bug Bounty",
    "취약점의 영향도를 설득력 있게 설명하기",
    "기술적인 재현 결과를 실제 비즈니스 영향과 연결해 명확한 리포트로 작성하는 방법을 다룹니다.",
    "2026. 08. 09",
    ["Impact", "Writing"],
  ],
  [
    "Development",
    "접근성을 고려한 다크 모드 토글 만들기",
    "키보드와 스크린 리더 사용자를 고려해 테마 전환 버튼에 필요한 상태와 레이블을 구성합니다.",
    "2026. 08. 02",
    ["A11y", "UI"],
  ],
  [
    "Web Security",
    "파일 업로드 기능을 안전하게 구현하는 기준",
    "확장자와 MIME 타입 검증부터 저장 경로 분리까지 업로드 기능에서 필요한 방어 방법을 정리합니다.",
    "2026. 07. 26",
    ["Upload", "Validation"],
  ],
  [
    "CTF",
    "웹 CTF 문제를 풀 때 사용하는 체크리스트",
    "문제의 입력 지점과 세션 흐름을 빠르게 파악하고 가설을 검증하는 순서를 간단히 정리했습니다.",
    "2026. 07. 19",
    ["CTF", "Checklist"],
  ],
].map(([category, title, content, date, tags], index) => ({
  id: index + 1,
  category,
  title,
  content: `${content} 이 글에서는 개념만 나열하지 않고 실제 상황에서 확인할 수 있는 기준과 적용 순서를 예시와 함께 단계별로 살펴봅니다. 마지막에는 직접 점검할 때 활용할 수 있는 체크리스트도 정리합니다. 각각의 항목이 왜 필요한지, 잘못 적용했을 때 어떤 문제가 발생하는지 확인하고 실무에서 바로 활용할 수 있는 형태로 내용을 구성했습니다. 테스트 과정에서 발견한 시행착오와 개선 방법도 함께 기록해 같은 문제를 다시 만났을 때 빠르게 대응할 수 있도록 했습니다. 환경에 따라 결과가 달라질 수 있는 부분은 별도로 구분하고 추가로 확인해야 하는 조건도 설명합니다.`,
  date,
  tags,
}));

function createPostPreview(content) {
  const plainText = content
    .replace(/<[^>]*>/g, " ")
    .replace(/!\[[^\]]*\]\([^)]*\)/g, " ")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/[`#>*_~]/g, "")
    .replace(/\s+/g, " ")
    .trim();

  return plainText.length > PREVIEW_LENGTH
    ? `${plainText.slice(0, PREVIEW_LENGTH)}…`
    : plainText;
}

function PostCard({
  post,
  selectedCategory,
  selectedTag,
  onCategoryClick,
  onTagClick,
}) {
  const navigate = useNavigate();
  const openPost = () => navigate(`/post/${post.id}`);

  return (
    <article
      className="postCard"
      aria-labelledby={`post-title-${post.id}`}
      role="link"
      tabIndex={0}
      onClick={openPost}
      onKeyDown={(event) => {
        if (event.key === "Enter") openPost();
      }}
    >
      <div className="postCardMeta">
        <button
          className={`postFilterButton postCategory ${selectedCategory === post.category ? "isActive" : ""}`}
          type="button"
          aria-pressed={selectedCategory === post.category}
          onClick={(event) => {
            event.stopPropagation();
            onCategoryClick(post.category);
          }}
        >
          {post.category}
        </button>
        <span>
          <FiCalendar aria-hidden="true" />
          <time>{post.date}</time>
        </span>
      </div>

      <h2 id={`post-title-${post.id}`}>{post.title}</h2>
      <p className="postExcerpt">{createPostPreview(post.content)}</p>

      <footer className="postCardFooter">
        <FiTag aria-hidden="true" />
        {post.tags.map((tag) => (
          <button
            className={`postFilterButton postTag ${selectedTag === tag ? "isActive" : ""}`}
            type="button"
            aria-pressed={selectedTag === tag}
            onClick={(event) => {
              event.stopPropagation();
              onTagClick(tag);
            }}
            key={tag}
          >
            #{tag}
          </button>
        ))}
      </footer>
    </article>
  );
}

function Home() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [pagination, setPagination] = useState({
    key: "|",
    count: POSTS_PER_PAGE,
  });
  const selectedCategory = searchParams.get("category") ?? "";
  const selectedTag = searchParams.get("tag") ?? "";
  const filterKey = `${selectedCategory}|${selectedTag}`;
  const visibleCount =
    pagination.key === filterKey ? pagination.count : POSTS_PER_PAGE;
  const filteredPosts = POSTS.filter(
    (post) =>
      (!selectedCategory || post.category === selectedCategory) &&
      (!selectedTag || post.tags.includes(selectedTag)),
  );
  const visiblePosts = filteredPosts.slice(0, visibleCount);
  const hasMorePosts = visibleCount < filteredPosts.length;

  const toggleFilter = (key, value) => {
    setSearchParams((currentParams) => {
      const nextParams = new URLSearchParams(currentParams);

      if (nextParams.get(key) === value) {
        nextParams.delete(key);
      } else {
        nextParams.set(key, value);
      }

      return nextParams;
    });
  };

  const clearFilters = () => setSearchParams({});

  return (
    <section className="postFeed" aria-label="게시글 목록">
      {(selectedCategory || selectedTag) && (
        <div className="activeFilters" aria-live="polite">
          <div>
            <span className="activeFiltersLabel">필터</span>
            {selectedCategory && <span>{selectedCategory}</span>}
            {selectedTag && <span>#{selectedTag}</span>}
            <strong>{filteredPosts.length}개의 글</strong>
          </div>
          <button type="button" onClick={clearFilters}>
            전체 보기
          </button>
        </div>
      )}

      <div className="postList">
        {visiblePosts.map((post) => (
          <PostCard
            key={post.id}
            post={post}
            selectedCategory={selectedCategory}
            selectedTag={selectedTag}
            onCategoryClick={(category) => toggleFilter("category", category)}
            onTagClick={(tag) => toggleFilter("tag", tag)}
          />
        ))}

        {filteredPosts.length === 0 && (
          <div className="emptyPosts">
            <p>선택한 조건에 맞는 글이 없습니다.</p>
            <button type="button" onClick={clearFilters}>
              필터 초기화
            </button>
          </div>
        )}
      </div>

      {hasMorePosts && (
        <button
          className="loadMoreButton"
          type="button"
          onClick={() =>
            setPagination({
              key: filterKey,
              count: visibleCount + POSTS_PER_PAGE,
            })
          }
        >
          Load More
        </button>
      )}
    </section>
  );
}

export default Home;
