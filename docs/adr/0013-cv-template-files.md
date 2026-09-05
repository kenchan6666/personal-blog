# Resume layouts besides classic-a4 live in the cv vault

Only the basic `classic-a4` layout stays in code. Every other ResumeTemplate is a JSON file at `template/{slug}.json` in the Owner's CvRepo, so names and section order can be edited in the CMS or the repo. Mongo still caches the file for PDF rendering. We rejected keeping those layouts as more builtins because a builtin cannot be renamed.
