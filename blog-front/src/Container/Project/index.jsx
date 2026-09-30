import {
  FiArrowLeft,
  FiArrowRight,
  FiCalendar,
  FiFolder,
  FiTag,
} from "react-icons/fi";
import { Link, useSearchParams } from "react-router-dom";
import Card from "../../Components/UI/Card";
import "./style.css";

const PROJECTS = [
  {
    id: "security-lab",
    title: "Web Security Lab",
    summary: "웹 취약점을 안전하게 재현하고 기록하기 위한 개인 실습 환경입니다.",
    description:
      "격리된 Docker 환경에서 웹 보안 취약점을 직접 재현하고, 공격 조건과 방어 방법을 함께 문서화합니다. 반복 가능한 실습 환경과 점검 체크리스트를 만드는 것이 목표입니다.",
    tags: ["Security", "Docker", "Research"],
    posts: [
      {
        id: "lab-environment",
        title: "로컬 보안 테스트 환경 구성",
        description:
          "Docker 네트워크를 분리하고 테스트 대상과 분석 도구를 안전하게 연결한 과정을 정리했습니다.",
        date: "2026. 09. 21",
        tags: ["Docker", "Lab"],
      },
      {
        id: "access-control-test",
        title: "접근 제어 테스트 시나리오 설계",
        description:
          "권한별 계정을 기준으로 객체와 기능 수준의 접근 제어를 확인하는 시나리오를 구성했습니다.",
        date: "2026. 09. 12",
        tags: ["Access Control", "OWASP"],
      },
    ],
  },
  {
    id: "blog-platform",
    title: "Personal Blog",
    summary: "React와 Vite로 제작하고 있는 개인 기술 블로그입니다.",
    description:
      "학습 기록과 프로젝트 경험을 빠르게 정리할 수 있도록 만든 블로그입니다. 반응형 레이아웃, 다크 모드, 카테고리와 태그 필터처럼 읽기 경험에 필요한 기능을 직접 구현하고 있습니다.",
    tags: ["React", "Vite", "CSS"],
    posts: [
      {
        id: "blog-structure",
        title: "확장 가능한 React 프로젝트 구조",
        description:
          "화면 단위 컨테이너와 재사용 컴포넌트를 분리하며 적용한 구조와 기준을 소개합니다.",
        date: "2026. 09. 18",
        tags: ["React", "Architecture"],
      },
      {
        id: "blog-theme",
        title: "CSS 변수로 다크 모드 구현하기",
        description:
          "색상 토큰을 분리하고 하나의 컴포넌트가 두 테마에서 자연스럽게 보이도록 개선했습니다.",
        date: "2026. 09. 03",
        tags: ["CSS", "Dark Mode"],
      },
      {
        id: "blog-filter",
        title: "카테고리와 태그 필터 연결",
        description:
          "URL 쿼리와 게시글 목록을 동기화해 공유 가능한 필터 기능을 구현한 과정을 기록했습니다.",
        date: "2026. 08. 27",
        tags: ["React Router", "UX"],
      },
    ],
  },
  {
    id: "recon-toolkit",
    title: "Recon Toolkit",
    summary: "반복적인 정찰 작업을 정리하고 자동화하는 도구 모음입니다.",
    description:
      "여러 출처에서 수집한 서브도메인과 서비스 정보를 하나의 흐름으로 정리합니다. 중복 제거, 응답 확인, 결과 분류 과정을 자동화하면서도 각 단계를 검증할 수 있도록 설계했습니다.",
    tags: ["Automation", "Recon", "CLI"],
    posts: [
      {
        id: "recon-pipeline",
        title: "서브도메인 정찰 파이프라인 만들기",
        description:
          "수집부터 검증까지 이어지는 작업을 작은 단계로 나누고 자동화한 방법을 설명합니다.",
        date: "2026. 08. 30",
        tags: ["Recon", "Automation"],
      },
      {
        id: "recon-output",
        title: "정찰 결과를 재사용 가능한 데이터로 정리하기",
        description:
          "도구마다 다른 출력 형식을 정규화하고 이후 점검에서 다시 활용할 수 있게 저장합니다.",
        date: "2026. 08. 16",
        tags: ["Data", "Workflow"],
      },
    ],
  },
];

function ProjectPost({ post }) {
  return (
    <article className="projectPost">
      <div className="projectPostMeta">
        <span>Project Log</span>
        <time>
          <FiCalendar aria-hidden="true" />
          {post.date}
        </time>
      </div>
      <h3>{post.title}</h3>
      <p>{post.description}</p>
      <footer>
        <FiTag aria-hidden="true" />
        {post.tags.map((tag) => (
          <span key={tag}>#{tag}</span>
        ))}
      </footer>
    </article>
  );
}

function Project() {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedId = searchParams.get("project");
  const selectedProject = PROJECTS.find((project) => project.id === selectedId);

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
            <div className="projectTags" aria-label="프로젝트 기술">
              {selectedProject.tags.map((tag) => (
                <span key={tag}>#{tag}</span>
              ))}
            </div>
          </div>
        </Card>

        <div className="projectPosts" aria-label="프로젝트 포스트">
          {selectedProject.posts.map((post) => (
            <ProjectPost post={post} key={post.id} />
          ))}
        </div>
      </section>
    );
  }

  return (
    <section className="projectArchive" aria-label="프로젝트 목록">
      <div className="projectGrid">
        {PROJECTS.map((project) => (
          <Link
            className="projectCard"
            to={`/project?project=${project.id}`}
            key={project.id}
          >
            <div className="projectCardTop">
              <FiFolder aria-hidden="true" />
              <span>{project.posts.length} Posts</span>
            </div>
            <h2>{project.title}</h2>
            <p>{project.summary}</p>
            <div className="projectCardFooter">
              <span>자세히 보기</span>
              <FiArrowRight aria-hidden="true" />
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
export default Project;
