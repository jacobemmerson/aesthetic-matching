const svg = (d, props) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}><path d={d} /></svg>
export const X = (p) => svg('M6 6l12 12M18 6L6 18', p)
export const ChevronLeft = (p) => svg('M15 5l-7 7 7 7', p)
export const ChevronRight = (p) => svg('M9 5l7 7-7 7', p)
export const Photos = (p) => svg('M4 7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2zM4 16l5-5 4 4 2-2 5 5M15 9.5h.01', p)
