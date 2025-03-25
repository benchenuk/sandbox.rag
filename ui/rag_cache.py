# ui/rag_cache.py
import streamlit as st

class CacheService:
    """Central cache management service"""
    def __init__(self, db):
        self.db = db
        self._init_cache_state()
    
    def _init_cache_state(self):
        """Initialize cache structures"""
        if 'task_cache' not in st.session_state:
            st.session_state.task_cache = {
                'version': 0,
                'tasks': {},
                'loaded': False
            }
    
    def load_cache(self):
        """Load/reload cache from DB"""
        if not st.session_state.task_cache['loaded']:
            tasks = self.db.get_all_tasks()
            st.session_state.task_cache['tasks'] = {t['id']: t for t in tasks}
            st.session_state.task_cache['version'] += 1
            st.session_state.task_cache['loaded'] = True
    
    def get_tasks(self, filter_tag=None):
        """Get cached tasks with optional filtering"""
        self.load_cache()
        if not filter_tag or filter_tag == 'All':
            return list(st.session_state.task_cache['tasks'].values())
        return [t for t in st.session_state.task_cache['tasks'].values()
                if filter_tag in t['tags'].split(',')]
    
    def invalidate_cache(self):
        """Mark cache as stale"""
        st.session_state.task_cache['loaded'] = False
