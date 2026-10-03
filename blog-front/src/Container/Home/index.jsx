import { useEffect, useState } from "react";
import { FiCalendar, FiTag } from "react-icons/fi";
import { useNavigate, useSearchParams } from "react-router-dom";
import { getPosts } from "../../api/post";
import "./style.css";

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
      {post.tags.length > 0 && (
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
      )}
    </article>
  );
}

function Home() {
  const [posts, setPosts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState("");
  const [searchParams, setSearchParams] = useSearchParams();
  const [nextPage, setNextPage] = useState(null);
  const [totalCount, setTotalCount] = useState(0);

  const selectedCategory = searchParams.get("category") ?? "";
  const selectedTag = searchParams.get("tag") ?? "";
  const searchQuery = searchParams.get("q")?.trim() ?? "";

  useEffect(() => {
    let active = true;
    getPosts({
      category: selectedCategory,
      tag: selectedTag,
      query: searchQuery,
    })
      .then((data) => {
        if (!active) return;
        setError("");
        if (Array.isArray(data)) {
          setPosts(data);
          setTotalCount(data.length);
          setNextPage(null);
          return;
        }
        setPosts(data.results ?? []);
        setTotalCount(data.count ?? 0);
        setNextPage(data.next ? 2 : null);
      })
      .catch(() => active && setError("게시글을 불러오지 못했습니다."))
      .finally(() => active && setIsLoading(false));
    return () => {
      active = false;
    };
  }, [searchQuery, selectedCategory, selectedTag]);

  const loadMore = async () => {
    if (!nextPage || isLoadingMore) return;
    setIsLoadingMore(true);
    setError("");
    try {
      const data = await getPosts({
        page: nextPage,
        category: selectedCategory,
        tag: selectedTag,
        query: searchQuery,
      });
      const nextPosts = Array.isArray(data) ? data : (data.results ?? []);
      setPosts((currentPosts) => [...currentPosts, ...nextPosts]);
      setNextPage(!Array.isArray(data) && data.next ? nextPage + 1 : null);
    } catch {
      setError("게시글을 더 불러오지 못했습니다.");
    } finally {
      setIsLoadingMore(false);
    }
  };

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
      {(selectedCategory || selectedTag || searchQuery) && (
        <div className="activeFilters" aria-live="polite">
          <div>
            <span className="activeFiltersLabel">필터</span>
            {selectedCategory && <span>{selectedCategory}</span>}
            {selectedTag && <span>#{selectedTag}</span>}
            {searchQuery && <span>“{searchQuery}” 검색</span>}
            <strong>{totalCount}개의 글</strong>
          </div>
          <button type="button" onClick={() => setSearchParams({})}>
            전체 보기
          </button>
        </div>
      )}
      <div className="postList">
        {posts.map((post) => (
          <PostCard
            key={post.id}
            post={post}
            selectedCategory={selectedCategory}
            selectedTag={selectedTag}
            onCategoryClick={(category) => toggleFilter("category", category)}
            onTagClick={(tag) => toggleFilter("tag", tag)}
          />
        ))}
        {posts.length === 0 && (
          <div className="emptyPosts">
            <p>게시글이 없습니다.</p>
          </div>
        )}
      </div>
      {nextPage && (
        <button
          className="loadMoreButton"
          type="button"
          onClick={loadMore}
          disabled={isLoadingMore}
        >
          {isLoadingMore ? "Loading…" : "Load More"}
        </button>
      )}
    </section>
  );
}

export default Home;
