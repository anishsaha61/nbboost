# Drop this file into ~/.ipython/profile_default/startup/ to enable nbboost in every notebook.
try:
    import nbboost

    nbboost.load()
except Exception as e:  # never break kernel start-up
    print(f"nbboost not loaded: {e}")
