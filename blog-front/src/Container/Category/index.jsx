import { useEffect, useMemo, useState } from "react";
import { FiFolder, FiTag } from "react-icons/fi";
import { Link } from "react-router-dom";
import { getAllPosts } from "../../api/post";
import Card from "../../Components/UI/Card";
import "./style.css";

function countValues(values) {
  return [...values.reduce((counts, value) => {
    counts.set(value, (counts.get(value) ?? 0) + 1);
    return counts;
  }, new Map())].map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
}

function Category() {
  const [posts, setPosts] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    getAllPosts()
      .then(setPosts)
      .catch(() => setError("카테고리 정보를 불러오지 못했습니다."));
  }, []);

  const categories = useMemo(() => countValues(posts.map((post) => post.category)), [posts]);
  const tags = useMemo(() => countValues(posts.flatMap((post) => post.tags)), [posts]);

  return (
    <Card>
      <section className="categoryArchive" aria-label="카테고리와 태그">
        {error && <p>{error}</p>}
        <div className="taxonomySection">
          <h2><FiFolder aria-hidden="true" />Categories</h2>
          <div className="taxonomyGrid">
            {categories.map(({ name, count }) => (
              <Link className="taxonomyItem categoryItem" to={`/?category=${encodeURIComponent(name)}`} key={name}>
                <span>{name}</span><strong aria-label={`${count}개의 글`}>{count}</strong>
              </Link>
            ))}
          </div>
        </div>
        {tags.length > 0 && (
          <div className="taxonomySection">
            <h2><FiTag aria-hidden="true" />Tags</h2>
            <div className="tagCloud">
              {tags.map(({ name, count }) => (
                <Link className="taxonomyItem tagItem" to={`/?tag=${encodeURIComponent(name)}`} key={name}>
                  <span>#{name}</span><strong aria-label={`${count}개의 글`}>{count}</strong>
                </Link>
              ))}
            </div>
          </div>
        )}
      </section>
    </Card>
  );
}

export default Category;
