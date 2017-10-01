Australie/Australia
Brasil/Brazil
Chili/Chile
Singapour/Singapore
Bielorussia/Belarus
Porto Rico/Puerto Rico
france/France
United States/USA
Vietnam/Viet Nam



SELECT luid, email, country, initials FROM scholars WHERE country REGEXP BINARY '^[a-z]';

UPDATE scholars SET country = "Australia" WHERE country = "Australie";
UPDATE scholars SET country = "Brazil" WHERE country = "Brasil";
UPDATE scholars SET country = "Chile" WHERE country = "Chili";
UPDATE scholars SET country = "Singapore" WHERE country = "Singapour";
UPDATE scholars SET country = "Belarus" WHERE country = "Bielorussia";
UPDATE scholars SET country = "Puerto Rico" WHERE country = "Porto Rico";
UPDATE scholars SET country = "France" WHERE country = "france";
UPDATE scholars SET country = "USA" WHERE country = "United States";
UPDATE scholars SET country = "Viet Nam" WHERE country = "Vietnam";
