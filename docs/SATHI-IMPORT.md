# SATHI / Dealer List Import — licensed DB 9 → 200+ kaise bharen
Fake entries MAT banao (jury risk). Real sources:

1. **SATHI portal** (Seed Traceability, Authentication & Holistic Inventory —
   seed traceability portal, Krishi Bhawan): licensed varieties + dealers dekho,
   CSC me `brand,product,batch_prefix,expiry,licensed=1` likho.
2. **State seed certification agency lists** (Haryana/Punjab): certified varieties.
3. **Dukaan survey**: packet se brand + batch-prefix + expiry note karo (photo saboot).

## CSV format (header zaroori nahi, pehli line skip hoti hai)
```
brand,product,batch_prefix,expiry,licensed
IFFCO,Guar HG-563,HG563,2027-10-31,1
KRIBHCO,Paddy Pusa-44,PUSA44,2027-03-31,1
```

## Upload
App → Home → Officer dashboard → Admin CSV → file chuno → Upload.
Har row `/api/admin/add_product` par jati hai; judne/chhootne ki ginti dikhti hai.
Galat row ho to DB se haath se hatana hoga ( IDs `products` table me ).

## Jury slide me likho
"Licensed list: SATHI + state certification + field survey, source-cited,
<audit date>. 200+ entries." — date aur source bina likhe claim mat karo.
