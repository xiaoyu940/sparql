SELECT pid, datname, backend_type
FROM pg_stat_activity
WHERE backend_type LIKE 'rs_ontop_core SPARQL Web Gateway %'
ORDER BY pid;
