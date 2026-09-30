import Markdown from 'react-markdown';
import './chatMarkdown.css';

type ChatMarkdownProps = {
  content: string;
};

export function ChatMarkdown({ content }: ChatMarkdownProps) {
  return <div className="workspace-markdown">
    <Markdown
      skipHtml
      components={{
        a: ({ children, href }) => <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>,
        img: ({ alt }) => alt ? <>[Image: {alt}]</> : null,
      }}
    >{content}</Markdown>
  </div>;
}
