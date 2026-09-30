import Card from "../../Components/UI/Card";
import { FiFolder, FiTag } from "react-icons/fi";
import { Link } from "react-router-dom";
import { POSTS } from "../Home";
import "./style.css";

function countValues(values) {
  return [...values.reduce((counts, value) => {
    counts.set(value, (counts.get(value) ?? 0) + 1);
    return counts;
  }, new Map())]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
}

function Category() {
  const categories = countValues(POSTS.map((post) => post.category));
  const tags = countValues(POSTS.flatMap((post) => post.tags));

  return (
    <Card>
      <section className="categoryArchive" aria-label="카테고리와 태그">
        <div className="taxonomySection">
          <h2>
            <FiFolder aria-hidden="true" />
            Categories
          </h2>
          <div className="taxonomyGrid">
            {categories.map(({ name, count }) => (
              <Link
                className="taxonomyItem categoryItem"
                to={`/?category=${encodeURIComponent(name)}`}
                key={name}
              >
                <span>{name}</span>
                <strong aria-label={`${count}개의 글`}>{count}</strong>
              </Link>
            ))}
          </div>
        </div>

        <div className="taxonomySection">
          <h2>
            <FiTag aria-hidden="true" />
            Tags
          </h2>
          <div className="tagCloud">
            {tags.map(({ name, count }) => (
              <Link
                className="taxonomyItem tagItem"
                to={`/?tag=${encodeURIComponent(name)}`}
                key={name}
              >
                <span>#{name}</span>
                <strong aria-label={`${count}개의 글`}>{count}</strong>
              </Link>
            ))}
          </div>
        </div>
      </section>
    </Card>
  );
}
export default Category;
