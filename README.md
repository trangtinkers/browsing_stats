Count most-visited domains from a browser history database, using [Datasette](https://datasette.io/).

# Requirements

`datasette`, installable with pip, uv, ...

# Usage

Browsers keep the history database locked while running, so work on a copy:

```bash
cp "/path/to/History" ./history.sqlite3
datasette ./history.sqlite3 --nolock
```

Then open the SQL editor in Datasette and run:

```sql
SELECT
  lower(
    substr(
      substr(url, instr(url, '://') + 3),
      1,
      CASE
        WHEN instr(substr(url, instr(url, '://') + 3), '/') = 0
          THEN length(substr(url, instr(url, '://') + 3))
        ELSE instr(substr(url, instr(url, '://') + 3), '/') - 1
      END
    )
  ) AS domain,
  SUM(visit_count) AS visits
FROM urls
WHERE url LIKE 'http%'
GROUP BY domain
ORDER BY visits DESC
LIMIT 50;
```

The query strips the scheme, cuts at the first `/` to isolate the host, and sums
`visit_count` per domain. Adjust `LIMIT` for a longer list.

This produces results such as:
| domain        | visits |
| ------------- | ------ |
| youtube.com   | 842    |
| github.com    | 517    |
| wikipedia.org | 301    |
