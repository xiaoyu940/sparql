SELECT ontop_refresh();
SELECT ontop_translate($$PREFIX ex: <http://example.org/>
SELECT ?firstName ?lastName ?salary
WHERE {
  ?emp ex:first_name ?firstName ;
       ex:last_name ?lastName ;
       ex:salary ?salary .
  {
    SELECT (AVG(?s) AS ?avgSal)
    WHERE { ?e ex:salary ?s }
  }
  FILTER(?salary > ?avgSal)
}
ORDER BY DESC(?salary)
LIMIT 10$$);
