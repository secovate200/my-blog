import { useEffect, useState } from "react";
import {
  FiArrowLeft,
  FiArrowRight,
  FiCalendar,
  FiFolder,
  FiTag,
} from "react-icons/fi";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { getProject, getProjects } from "../../api/project";
import Card from "../../Components/UI/Card";
import "./style.css";

const PREVIEW_LENGTH = 180;

function createPreview(content = "") {
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

function ProjectPost({ post, projectId, selectedTag, onTagClick }) {
  const navigate = useNavigate();
  const detailUrl = `/project/${projectId}/post/${post.id}${
    selectedTag ? `?tag=${encodeURIComponent(selectedTag)}` : ""
  }`;
  const openPost = () => navigate(detailUrl);

  return (
    <article
      className="projectPost"
      aria-labelledby={`project-post-title-${post.id}`}
      role="link"
      tabIndex={0}
      onClick={openPost}
      onKeyDown={(event) => event.key === "Enter" && openPost()}
    >
      <div className="projectPostMeta">
        <span>Project Log</span>
        <time dateTime={post.created_at}>
          <FiCalendar aria-hidden="true" />
          {formatDate(post.created_at)}
        </time>
      </div>
      <h3 id={`project-post-title-${post.id}`}>{post.title}</h3>
      <p>{createPreview(post.content)}</p>
      {post.tags.length > 0 && (
        <footer>
          <FiTag aria-hidden="true" />
          {post.tags.map((tag) => (
            <button
              className={selectedTag === tag ? "isActive" : ""}
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

function ProjectMessage({ children }) {
  return (
    <section className="projectArchive">
      <div className="projectState" role="status">
        <p>{children}</p>
      </div>
    </section>
  );
}

function Project() {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedId = searchParams.get("project");
  const selectedTag = searchParams.get("tag") ?? "";
  const requestKey = selectedId ? `detail:${selectedId}` : "list";
  const [requestState, setRequestState] = useState({
    key: null,
    projects: [],
    selectedProject: null,
    error: "",
  });
  const { projects, selectedProject, error } = requestState;
  const isLoading = requestState.key !== requestKey;
  const visiblePosts = selectedProject
    ? selectedProject.posts.filter(
        (post) => !selectedTag || post.tags.includes(selectedTag),
      )
    : [];

  const toggleTag = (tag) => {
    const nextParams = new URLSearchParams(searchParams);
    if (selectedTag === tag) nextParams.delete("tag");
    else nextParams.set("tag", tag);
    setSearchParams(nextParams);
  };

  useEffect(() => {
    let active = true;

    const request = selectedId ? getProject(selectedId) : getProjects();
    request
      .then((data) => {
        if (!active) return;
        setRequestState({
          key: requestKey,
          projects: selectedId
            ? []
            : Array.isArray(data)
              ? data
              : (data.results ?? []),
          selectedProject: selectedId ? data : null,
          error: "",
        });
      })
      .catch((requestError) => {
        if (!active) return;
        setRequestState({
          key: requestKey,
          projects: [],
          selectedProject: null,
          error:
            requestError.response?.status === 404
              ? "존재하지 않거나 공개되지 않은 프로젝트입니다."
              : "프로젝트를 불러오지 못했습니다.",
        });
      });

    return () => {
      active = false;
    };
  }, [requestKey, selectedId]);

  if (isLoading) return <ProjectMessage>프로젝트를 불러오는 중입니다.</ProjectMessage>;

  if (error) {
    return (
      <section className="projectArchive">
        <div className="projectState" role="alert">
          <p>{error}</p>
          {selectedId && (
            <button type="button" onClick={() => setSearchParams({})}>
              프로젝트 목록
            </button>
          )}
        </div>
      </section>
    );
  }

  if (selectedProject) {
    return (
      <section className="projectDetail" aria-labelledby="project-detail-title">
        <Card>
          <div className="projectDetailIntro">
            <button type="button" onClick={() => setSearchParams({})}>
              <FiArrowLeft aria-hidden="true" />
              프로젝트 목록
            </button>
            <span className="projectEyebrow">Project</span>
            <h1 id="project-detail-title">{selectedProject.title}</h1>
            <p>{selectedProject.description}</p>
            {selectedProject.tags.length > 0 && (
              <div className="projectTags" aria-label="프로젝트 기술">
                {selectedProject.tags.map((tag) => (
                  <button
                    className={selectedTag === tag ? "isActive" : ""}
                    type="button"
                    aria-pressed={selectedTag === tag}
                    onClick={() => toggleTag(tag)}
                    key={tag}
                  >
                    #{tag}
                  </button>
                ))}
              </div>
            )}
          </div>
        </Card>

        <div className="projectPosts" aria-label="프로젝트 포스트">
          {visiblePosts.map((post) => (
            <ProjectPost
              post={post}
              projectId={selectedProject.id}
              selectedTag={selectedTag}
              onTagClick={toggleTag}
              key={post.id}
            />
          ))}
          {visiblePosts.length === 0 && (
            <div className="projectState">
              <p>
                {selectedTag
                  ? `#${selectedTag} 태그의 프로젝트 글이 없습니다.`
                  : "공개된 프로젝트 글이 없습니다."}
              </p>
              {selectedTag && (
                <button type="button" onClick={() => toggleTag(selectedTag)}>
                  전체 프로젝트 글
                </button>
              )}
            </div>
          )}
        </div>
      </section>
    );
  }

  return (
    <section className="projectArchive" aria-label="프로젝트 목록">
      <div className="projectGrid">
        {projects.map((project) => (
          <Link
            className="projectCard"
            to={`/project?project=${project.id}`}
            key={project.id}
          >
            <div className="projectCardTop">
              <FiFolder aria-hidden="true" />
              <span>{project.post_count} Posts</span>
            </div>
            <h2>{project.title}</h2>
            <p>{createPreview(project.description)}</p>
            <div className="projectCardFooter">
              <span>자세히 보기</span>
              <FiArrowRight aria-hidden="true" />
            </div>
          </Link>
        ))}
      </div>
      {projects.length === 0 && (
        <div className="projectState">
          <p>공개된 프로젝트가 없습니다.</p>
        </div>
      )}
    </section>
  );
}

export default Project;
