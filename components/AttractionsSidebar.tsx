'use client';

import { useState } from 'react';
import { Place } from '@/types';

interface Props {
  destination: string | null;
  places: Place[];
  loading: boolean;
}

const CATEGORY_ICONS: Record<string, string> = {
  temple: '🛕',
  shrine: '⛩️',
  museum: '🏛️',
  park: '🌳',
  beach: '🏖️',
  palace: '🏯',
  market: '🛍️',
  tower: '🗼',
  castle: '🏰',
  garden: '🌸',
  monument: '🗿',
  church: '⛪',
  mosque: '🕌',
  lake: '🏞️',
  mountain: '⛰️',
  island: '🏝️',
};

function categoryIcon(category: string): string {
  const key = category.toLowerCase();
  for (const [k, v] of Object.entries(CATEGORY_ICONS)) {
    if (key.includes(k)) return v;
  }
  return '📍';
}

function PlaceCard({ place }: { place: Place }) {
  const [imgFailed, setImgFailed] = useState(false);
  const isFree = place.estimated_cost_usd === 0;

  return (
    <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden hover:bg-white/[0.08] hover:border-white/20 transition-all duration-200 group">
      {/* Image */}
      <div className="relative h-36 overflow-hidden bg-white/5">
        {place.image_url && !imgFailed ? (
          <img
            src={place.image_url}
            alt={place.name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            onError={() => setImgFailed(true)}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <span className="text-5xl opacity-30">{categoryIcon(place.category)}</span>
          </div>
        )}
        {/* Category badge */}
        <span className="absolute top-2 left-2 text-xs px-2 py-0.5 rounded-full bg-black/60 backdrop-blur-sm text-white/80 border border-white/10">
          {categoryIcon(place.category)} {place.category}
        </span>
        {/* Cost badge */}
        <span
          className={`absolute top-2 right-2 text-xs px-2 py-0.5 rounded-full backdrop-blur-sm font-medium border ${
            isFree
              ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
              : 'bg-amber-500/20 text-amber-300 border-amber-500/30'
          }`}
        >
          {isFree ? 'Free' : place.cost_note}
        </span>
      </div>

      {/* Info */}
      <div className="p-3.5">
        <h4 className="text-white font-semibold text-sm mb-1 leading-snug">{place.name}</h4>
        <p className="text-white/50 text-xs leading-relaxed line-clamp-2">{place.description}</p>
      </div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden animate-pulse">
      <div className="h-36 bg-white/10" />
      <div className="p-3.5 space-y-2">
        <div className="h-3 bg-white/10 rounded w-3/4" />
        <div className="h-2.5 bg-white/10 rounded w-full" />
        <div className="h-2.5 bg-white/10 rounded w-2/3" />
      </div>
    </div>
  );
}

export default function AttractionsSidebar({ destination, places, loading }: Props) {
  return (
    <aside className="w-72 flex-shrink-0">
      <div className="sticky top-24 max-h-[calc(100vh-7rem)] overflow-y-auto pr-1 space-y-4 scrollbar-thin">
        {/* Header */}
        <div className="flex items-center gap-2">
          <span className="text-lg">🗺️</span>
          <div>
            <h3 className="text-white font-semibold text-sm">Places to Visit</h3>
            {destination && (
              <p className="text-white/40 text-xs">in {destination}</p>
            )}
          </div>
        </div>

        {/* Loading skeletons */}
        {loading && places.length === 0 && (
          <>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </>
        )}

        {/* Place cards */}
        {places.map((place) => (
          <PlaceCard key={place.name} place={place} />
        ))}

        {/* Empty state (after loading, no results) */}
        {!loading && places.length === 0 && (
          <div className="text-center py-8 text-white/30 text-sm">
            No attraction data available
          </div>
        )}
      </div>
    </aside>
  );
}
