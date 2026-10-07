import { useRef, useState } from "react";
import "./Write.css";
import { createPost, createResearchPost, updatePost, updateResearchPost } from "../../api";
import { editorJsToPlainText } from "../../utils/editorContent";
import { navigateToErrorPage } from "../../utils/errorNavigation";
import EditorJsEditor from "./EditorJsEditor";

export const WriteContent = ({
  theme,
  categoryOptions = ["개발", "보안", "백엔드", "데이터베이스", "기타"],
  initialCategory = "",
  defaultVisibility = "public",
  titlePlaceholder = "게시글 제목",
  postType = "blog",
  initialPost = null,
}) => {
  const [message, setMessage] = useState("");
  const editorRef = useRef(null);

  const prepareSubmission = async (form, status) => {
    const formData = new FormData(form);
    if (!editorRef.current) {
      setMessage("편집기를 불러오는 중입니다. 잠시 후 다시 시도해 주세요.");
      return;
    }
    await editorRef.current.isReady;
    const editorData = await editorRef.current.save();
    const content = JSON.stringify(editorData);
    const markdown = editorJsToPlainText(editorData);

    formData.set("status", status);
    formData.set("postType", postType);
    formData.set("contentBlocks", content);
    formData.set("contentMarkdown", markdown);

    setMessage("저장하는 중입니다...");
    try {
      const common = { title: formData.get("title"), status, visibility: formData.get("visibility"), content, contentMarkdown: markdown };
      if (postType === "research") {
        const postData = { ...common, project: formData.get("category"), summary: markdown.slice(0, 500) };
        const savedPost = initialPost ? await updateResearchPost(initialPost.id, postData) : await createResearchPost(postData);
        setMessage(initialPost ? "연구 글을 수정했습니다." : status === "draft" ? "연구 글을 임시 저장했습니다." : "연구 글을 게시했습니다.");
        window.location.hash = initialPost ? `/research-view?id=${encodeURIComponent(savedPost.id)}` : "/research";
      } else {
        const postData = { ...common, category: formData.get("category"), tags: formData.get("tags") };
        const savedPost = initialPost ? await updatePost(initialPost.id, postData) : await createPost(postData);
        setMessage(initialPost ? "게시글을 수정했습니다." : status === "draft" ? "게시글을 임시 저장했습니다." : "게시글을 게시했습니다.");
        window.location.hash = initialPost ? `/blog-view?id=${encodeURIComponent(savedPost.id)}` : "/blog";
      }
    } catch (error) {
      navigateToErrorPage(error);
    }
  };

  return (
    <main className="content write-content">
      <form
        className="write-panel"
        onSubmit={(event) => {
          event.preventDefault();
          prepareSubmission(event.currentTarget, "published");
        }}
      >
        <section className="write-document" aria-labelledby="post-editor-title">
          <input
            className="write-title-input"
            name="title"
            aria-label="게시글 제목"
            placeholder={titlePlaceholder}
            defaultValue={initialPost?.title ?? ""}
            required
          />
          <h2 id="post-editor-title" className="visually-hidden">
            게시글 본문
          </h2>
          <EditorJsEditor
            editorRef={editorRef}
            initialContent={initialPost?.content ?? ""}
          />
          <p className="editorjs-help">
            <kbd>/</kbd>를 입력해 제목, 목록, 코드, 이미지, 파일 등의 블록을
            추가할 수 있습니다.
          </p>
        </section>

        <footer className="write-submit-bar">
          <label className="write-field write-category">
            <span>카테고리</span>
            <select name="category" defaultValue={initialCategory} required>
              <option value="" disabled>
                선택
              </option>
              {categoryOptions.map((category) => (
                <option value={category.id ?? category} key={category.id ?? category}>
                  {category.name ?? category}
                </option>
              ))}
            </select>
          </label>
          <label className="write-field write-tags">
            <span>태그</span>
            <input name="tags" placeholder="태그 입력" defaultValue={initialPost?.tags ?? ""} />
          </label>
          <label className="write-field write-visibility">
            <span>공개 상태</span>
            <select name="visibility" defaultValue={defaultVisibility}>
              <option value="public">전체 공개</option>
              <option value="private">비공개</option>
            </select>
          </label>
          <p className="write-message" role="status" aria-live="polite">
            {message}
          </p>
          <div className="publish-actions">
            <button
              className="write-secondary"
              type="button"
              onClick={(event) =>
                prepareSubmission(event.currentTarget.form, "draft")
              }
            >
              임시 저장
            </button>
            <button className="settings-save" type="submit">
              {initialPost ? "수정 완료" : "게시하기"}
            </button>
          </div>
        </footer>
      </form>
    </main>
  );
};
