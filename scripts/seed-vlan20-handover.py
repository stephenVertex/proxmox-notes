import json,sys,time,ipaddress,re
def build_seed(rows,reservations,now,max_old_lease_seconds=7200):
    pool=ipaddress.ip_network("192.168.20.0/24")
    seen_ip=set(); seen_mac=set(); seen_cid=set(); output=[]
    for row in rows:
        ip=ipaddress.ip_address(row["ip"])
        mac=row["mac"].lower().replace("-",":")
        if not re.fullmatch(r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}",mac):
            raise ValueError("Invalid MAC: "+mac)
        if ip not in pool or ip.packed[-1] in (0,255):
            raise ValueError("Not a VLAN20 host address: "+str(ip))
        inside=20<=int(str(ip).split(".")[-1])<=119
        if not inside and reservations.get(str(ip))!=mac:
            raise ValueError("Outside pool without matching staged reservation: "+str(ip))
        if ip in seen_ip or mac in seen_mac:
            raise ValueError("Duplicate IP or MAC")
        seen_ip.add(ip); seen_mac.add(mac)
        raw=row.get("client_id") or "*"
        if raw!="*":
            raw=raw.lower().replace(":","").replace("-","")
            if not re.fullmatch(r"(?:[0-9a-f]{2}){1,255}",raw):
                raise ValueError("Client ID must be hexadecimal octets")
            if raw in seen_cid:raise ValueError("Duplicate client ID")
            seen_cid.add(raw)
            raw=":".join(raw[i:i+2] for i in range(0,len(raw),2))
        expiry=int(row["expires_epoch"])
        if expiry==0:
            if inside:raise ValueError("Infinite pool lease requires explicit reconciliation")
            until=0
        elif expiry<=now:
            raise ValueError("Expired input lease; refresh snapshot")
        else:
            until=max(expiry,now+max_old_lease_seconds+300)
        output.append(f"{until} {mac} {ip} * {raw}")
    if not output:raise ValueError("Empty seed")
    return "\n".join(output)+"\n"

if __name__=="__main__":
    rows=json.load(open(sys.argv[1]))
    reservations={}
    for line in open(sys.argv[2]):
        if line.startswith("dhcp-host="):
            fields=line.split("=",1)[1].strip().split(",")
            if len(fields)>=2:
                try:ipaddress.ip_address(fields[1])
                except ValueError:continue
                reservations[fields[1]]=fields[0].lower()
    sys.stdout.write(build_seed(rows,reservations,int(time.time())))
