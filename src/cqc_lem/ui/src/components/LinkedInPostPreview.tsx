interface LinkedInPostPreviewProps {
  content: string
  author?: string
  headline?: string
  mediaUrl?: string
}

export default function LinkedInPostPreview({
  content,
  author = 'Your Name',
  headline = 'Your Headline',
  mediaUrl,
}: LinkedInPostPreviewProps) {
  const lines = content.split('\n')
  const preview = lines.slice(0, 3).join('\n')
  const hasMore = lines.length > 3 || content.length > 300

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm max-w-lg font-sans">
      {/* Header */}
      <div className="flex items-center gap-3 p-4">
        <div className="w-12 h-12 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold text-lg flex-shrink-0">
          {author.charAt(0).toUpperCase()}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1">
            <span className="font-semibold text-gray-900 text-sm truncate">{author}</span>
            <span className="text-gray-400 text-xs">• 1st</span>
          </div>
          <p className="text-xs text-gray-500 truncate">{headline}</p>
          <div className="flex items-center gap-1 text-xs text-gray-400 mt-0.5">
            <span>Just now</span>
            <span>·</span>
            <svg className="w-3 h-3" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 0C3.58 0 0 3.58 0 8s3.58 8 8 8 8-3.58 8-8-3.58-8-8-8zM7 11.5L3.5 8l1.41-1.41L7 8.67l4.59-4.58L13 5.5 7 11.5z"/>
            </svg>
          </div>
        </div>
        <button className="text-blue-600 border border-blue-600 rounded-full px-3 py-1 text-xs font-semibold hover:bg-blue-50">
          + Follow
        </button>
      </div>

      {/* Content */}
      <div className="px-4 pb-3">
        <p className="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">
          {hasMore ? preview : content}
          {hasMore && (
            <span className="text-gray-500 cursor-pointer"> …<span className="text-blue-600"> see more</span></span>
          )}
        </p>
      </div>

      {/* Media */}
      {mediaUrl && (
        <div className="bg-gray-100 aspect-video overflow-hidden">
          <img src={mediaUrl} alt="Post media" className="w-full h-full object-cover" />
        </div>
      )}

      {/* Stats bar */}
      <div className="px-4 py-2 flex items-center justify-between text-xs text-gray-500 border-t border-gray-100">
        <div className="flex items-center gap-1">
          <span className="text-blue-600">👍</span>
          <span>Be the first to react</span>
        </div>
        <span>0 comments</span>
      </div>

      {/* Action buttons */}
      <div className="flex items-center border-t border-gray-100">
        {['👍 Like', '💬 Comment', '🔁 Repost', '📤 Send'].map((action) => (
          <button
            key={action}
            className="flex-1 py-3 text-xs font-semibold text-gray-500 hover:bg-gray-50 flex items-center justify-center gap-1"
          >
            {action}
          </button>
        ))}
      </div>
    </div>
  )
}
