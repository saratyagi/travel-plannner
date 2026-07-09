'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Props {
  report: string;
  onReset: () => void;
}

export default function TripReport({ report, onReset }: Props) {
  const handleCopy = () => {
    navigator.clipboard.writeText(report);
  };

  return (
    <div className="w-full max-w-4xl mx-auto animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-white">Your Travel Plan</h2>
        <div className="flex gap-3">
          <button
            onClick={handleCopy}
            className="px-4 py-2 text-sm rounded-lg bg-white/10 hover:bg-white/20 text-white/80 transition-colors"
          >
            Copy Markdown
          </button>
          <button
            onClick={onReset}
            className="px-4 py-2 text-sm rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium transition-colors"
          >
            Plan Another Trip
          </button>
        </div>
      </div>

      <div className="bg-white/5 border border-white/10 rounded-2xl p-8 prose prose-invert prose-sm max-w-none
        prose-headings:text-white prose-headings:font-bold
        prose-h1:text-2xl prose-h1:border-b prose-h1:border-white/20 prose-h1:pb-3
        prose-h2:text-lg prose-h2:text-blue-300 prose-h2:mt-8
        prose-p:text-white/80 prose-p:leading-relaxed
        prose-strong:text-white
        prose-table:w-full
        prose-thead:bg-white/10
        prose-th:text-white/90 prose-th:font-semibold prose-th:px-4 prose-th:py-2
        prose-td:text-white/75 prose-td:px-4 prose-td:py-2 prose-td:border-white/10
        prose-tr:border-white/10 prose-tr:hover:bg-white/5
        prose-blockquote:border-blue-400 prose-blockquote:text-white/60
        prose-code:text-blue-300 prose-code:bg-white/10 prose-code:px-1 prose-code:rounded
        overflow-x-auto"
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{report}</ReactMarkdown>
      </div>
    </div>
  );
}
