import { useEffect, useMemo, useState } from "react";
import { FiCalendar, FiTag } from "react-icons/fi";
import { useNavigate, useSearchParams } from "react-router-dom";
import { getPosts } from "../../api/post";
import "./style.css";

const POSTS_PER_PAGE = 10;
const PREVIEW_LENGTH = 250;

function createPostPreview(content = "") {
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

function formatDate(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(value));
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
      onKeyDown={(event) => event.key === "Enter" && openPost()}
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
          <time dateTime={post.created_at}>{formatDate(post.created_at)}</time>
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
  const [posts, setPosts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchParams, setSearchParams] = useSearchParams();
  const [pagination, setPagination] = useState({
    key: "|",
    count: POSTS_PER_PAGE,
  });

  useEffect(() => {
    let active = true;
    getPosts()
      .then(
        (data) =>
          active && setPosts(Array.isArray(data) ? data : (data.results ?? [])),
      )
      .catch(() => active && setError("게시글을 불러오지 못했습니다."))
      .finally(() => active && setIsLoading(false));
    return () => {
      active = false;
    };
  }, []);

  const selectedCategory = searchParams.get("category") ?? "";
  const selectedTag = searchParams.get("tag") ?? "";
  const filterKey = `${selectedCategory}|${selectedTag}`;
  const visibleCount =
    pagination.key === filterKey ? pagination.count : POSTS_PER_PAGE;
  const filteredPosts = useMemo(
    () =>
      posts.filter(
        (post) =>
          (!selectedCategory || post.category === selectedCategory) &&
          (!selectedTag || post.tags.includes(selectedTag)),
      ),
    [posts, selectedCategory, selectedTag],
  );
  const visiblePosts = filteredPosts.slice(0, visibleCount);

  const toggleFilter = (key, value) =>
    setSearchParams((currentParams) => {
      const nextParams = new URLSearchParams(currentParams);
      if (nextParams.get(key) === value) nextParams.delete(key);
      else nextParams.set(key, value);
      return nextParams;
    });

  if (isLoading)
    return (
      <section className="postFeed">
        <div className="emptyPosts">
          <p>게시글을 불러오는 중입니다.</p>
        </div>
      </section>
    );
  if (error)
    return (
      <section className="postFeed">
        <div className="emptyPosts">
          <p>{error}</p>
        </div>
      </section>
    );

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
          <button type="button" onClick={() => setSearchParams({})}>
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
            <p>게시글이 없습니다.</p>
          </div>
        )}
      </div>
      {visibleCount < filteredPosts.length && (
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
