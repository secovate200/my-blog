import { FiArrowLeft, FiCalendar, FiTag } from "react-icons/fi";
import { Link, useParams } from "react-router-dom";
import Card from "../../Components/UI/Card";
import { POSTS } from "../Home";
import "./style.css";

const SECTION_TITLES = ["개요", "핵심 내용", "적용 방법", "점검 체크리스트"];

function createPostSections(content) {
  const sentences = content.split(/(?<=[.!?。])\s+/);

  return sentences.reduce((sections, sentence, index) => {
    const sectionIndex = Math.floor(index / 3);

    if (!sections[sectionIndex]) {
      sections[sectionIndex] = {
        id: `section-${sectionIndex + 1}`,
        title: SECTION_TITLES[sectionIndex] ?? `추가 내용 ${sectionIndex + 1}`,
        content: sentence,
      };
    } else {
      sections[sectionIndex].content += ` ${sentence}`;
    }

    return sections;
  }, []);
}

export function PostTableOfContents({ postId }) {
  const post = POSTS.find((item) => item.id === Number(postId));

  if (!post) return null;

  const sections = createPostSections(post.content);

  return (
    <nav className="postTableOfContents" aria-label="목차">
      <strong>목차</strong>
      <ol>
        {sections.map((section) => (
          <li key={section.id}>
            <a href={`#${section.id}`}>{section.title}</a>
          </li>
        ))}
      </ol>
    </nav>
  );
}

function PostDetail() {
  const { postId } = useParams();
  const post = POSTS.find((item) => item.id === Number(postId));

  if (!post) {
    return (
      <Card>
        <section className="postNotFound">
          <span>404</span>
          <h1>게시글을 찾을 수 없습니다.</h1>
          <Link to="/">
            <FiArrowLeft aria-hidden="true" />
            게시글 목록
          </Link>
        </section>
      </Card>
    );
  }

  const sections = createPostSections(post.content);

  return (
    <div className="postDetailLayout">
      <Card>
        <article className="postDetail" aria-labelledby="post-detail-title">
        <Link className="postBackLink" to="/">
          <FiArrowLeft aria-hidden="true" />
          게시글 목록
        </Link>

        <header className="postDetailHeader">
          <div className="postDetailMeta">
            <Link to={`/?category=${encodeURIComponent(post.category)}`}>
              {post.category}
            </Link>
            <time>
              <FiCalendar aria-hidden="true" />
              {post.date}
            </time>
          </div>
          <h1 id="post-detail-title">{post.title}</h1>
          <div className="postDetailTags">
            <FiTag aria-hidden="true" />
            {post.tags.map((tag) => (
              <Link to={`/?tag=${encodeURIComponent(tag)}`} key={tag}>
                #{tag}
              </Link>
            ))}
          </div>
        </header>

          <div className="postDetailBody">
            {sections.map((section) => (
              <section id={section.id} className="postSection" key={section.id}>
                <h2>{section.title}</h2>
                <p>{section.content}</p>
              </section>
            ))}
          </div>
        </article>
      </Card>
    </div>
  );
}

export default PostDetail;
