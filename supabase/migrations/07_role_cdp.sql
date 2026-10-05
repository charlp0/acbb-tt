-- Rôle « cdp » (sous-sportive du Championnat de Paris, 05/10/2026) : un lien de ce rôle n'ouvre que les outils
-- du CDP (dispos et compositions), jamais le championnat par équipe ni l'administration des accès.
alter table public.liens drop constraint if exists liens_role_check;
alter table public.liens add constraint liens_role_check check (role in ('capitaine', 'sportive', 'cdp'));
