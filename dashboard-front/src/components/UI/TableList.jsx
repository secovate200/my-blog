export const posts = [
  {
    id: "25",
    title: "Building a safer authentication flow",
    category: "Security",
    status: "Published",
    date: "Sep 07, 2026",
  },
  {
    id: "24",
    title: "Building a safer authentication flow",
    category: "Security",
    status: "Published",
    date: "Sep 07, 2026",
  },
  {
    id: "23",
    title: "What I learned from rebuilding the dashboard",
    category: "Development",
    status: "Draft",
    date: "Sep 06, 2026",
  },
  {
    id: "22",
    title: "A practical guide to request logging",
    category: "Backend",
    status: "Published",
    date: "Sep 04, 2026",
  },
  {
    id: "21",
    title: "Designing a calm writing workflow",
    category: "Writing",
    status: "Review",
    date: "Sep 01, 2026",
  },
  ...Array.from({ length: 21 }, (_, index) => {
    const id = 20 - index;
    const titles = [
      "Improving API error responses",
      "Notes on accessible interface design",
      "Deploying a small service with confidence",
      "A checklist for reviewing pull requests",
      "Understanding database indexes",
    ];
    const categories = [
      "Backend",
      "Design",
      "Security",
      "Development",
      "Database",
    ];
    const statuses = ["Published", "Draft", "Review"];

    return {
      id: String(id),
      title: titles[index % titles.length],
      category: categories[index % categories.length],
      status: statuses[index % statuses.length],
      date: `Aug ${String(31 - index).padStart(2, "0")}, 2026`,
    };
  }),
];

const TableList = ({
  items = posts.slice(0, 5),
  title = "Recent posts",
  showViewAll = true,
  onViewAll,
  viewAllLabel = "View all",
  footer = null,
  minimumRows = 0,
  linkTitles = false,
  labels = ["ID", "Title", "Category", "Status", "Updated"],
}) => {
  const titleId = title.toLowerCase().replace(/\s+/g, "-");
  const emptyRows = Math.max(minimumRows - items.length, 0);

  return (
    <section className="table-list" aria-labelledby={titleId}>
      <div className="table-list--header">
        <h2 id={titleId}>{title}</h2>
        {showViewAll && (
          <button className="view-all" type="button" onClick={onViewAll}>
            {viewAllLabel}
          </button>
        )}
      </div>

      <div className="table-list--scroll">
        <div className="post-list" role="table" aria-label={title}>
          <div className="post-list--head post-list--row" role="row">
            {labels.map((label) => (
              <span role="columnheader" key={label}>
                {label}
              </span>
            ))}
          </div>
          <div className="post-list--body" role="rowgroup">
            {items.map((post, index) => (
              <div
                className={`post-list--row ${emptyRows > 0 && index === items.length - 1 ? "post-list--row-last-filled" : ""}`}
                role="row"
                key={post.id}
              >
                <span className="post-id" role="cell">
                  {post.displayId ?? post.id}
                </span>
                <span className="post-title" role="cell">
                  {linkTitles ? <a href={`#/blog-view?id=${encodeURIComponent(post.id)}`}>{post.title}</a> : post.title}
                </span>
                <span role="cell">{post.category}</span>
                <span role="cell">
                  <span
                    className={`status status--${post.status.toLowerCase()}`}
                  >
                    {post.status}
                  </span>
                </span>
                <span role="cell">{post.date}</span>
              </div>
            ))}
            {Array.from({ length: emptyRows }, (_, index) => (
              <div
                className="post-list--row post-list--row-empty"
                role="row"
                aria-hidden="true"
                key={`empty-${index}`}
              >
                <span />
                <span />
                <span />
                <span />
                <span />
              </div>
            ))}
          </div>
        </div>
      </div>
      {footer}
    </section>
  );
};

export default TableList;
