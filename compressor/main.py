import json, sys, struct

def compress(json_path, out_path):
    with open(json_path) as f:
        data = json.load(f)

    teams = data["info"]["teams"]
    team_idx = {name: i for i, name in enumerate(teams)}

    players = []
    team_player_counts = []

    players_by_team = data["info"]["players"]
    for team in teams:
        roster = players_by_team[team]
        team_player_counts.append(len(roster))
        players.extend(roster)
    player_idx = {name: i for i, name in enumerate(players)}

    delivery_bits = []
    wicket_bits = []
    wicket_table = []
    innings_layout = []

    for inning in data["innings"]:
        overs = inning["overs"] if "overs" in inning else []
        inning_team = inning["team"]
        inning_team_idx = team_idx[inning_team]

        over_delivery_counts = []
        for over in overs:
            over_deliveries = over["deliveries"]
            over_delivery_counts.append(len(over_deliveries))
            for d in over_deliveries:
                b = player_idx[d["batter"]]
                bw = player_idx[d["bowler"]]
                ns = player_idx[d["non_striker"]]
                runs = d["runs"]["batter"]
                extras = 1 if d["runs"]["extras"] else 0
                has_wicket = 1 if "wickets" in d else 0
                val = (b << 15) | (bw << 10) | (ns << 5) | (runs << 2) | (extras << 1) | has_wicket

                delivery_bits.append(val)
                wicket_bits.append(has_wicket)

                if has_wicket:
                    w = d["wickets"][0]
                    po = player_idx[w["player_out"]]
                    fielder = 0
                    if "fielders" in w and w["fielders"]:
                        first_fielder = w["fielders"][0]
                        if "name" in first_fielder:
                            fielder_name = first_fielder["name"]
                            if fielder_name in player_idx:
                                fielder = player_idx[fielder_name]
                    kind = 1 if w["kind"] == "caught" else 0
                    wicket_table.append((po << 6) | (fielder << 1) | kind)

        innings_layout.append(
            {
                "team_index": inning_team_idx,
                "over_delivery_counts": over_delivery_counts,
            }
        )

    with open(out_path, "wb") as f:
        f.write(struct.pack(">HH", len(players), len(delivery_bits)))

        for name in players:
            f.write(name.encode() + b"\x00")

        f.write(struct.pack(">B", len(teams)))
        for name in teams:
            f.write(name.encode() + b"\x00")
        for count in team_player_counts:
            f.write(struct.pack(">B", count))

        f.write(struct.pack(">B", len(innings_layout)))
        for inning in innings_layout:
            f.write(struct.pack(">B", inning["team_index"]))
            f.write(struct.pack(">B", len(inning["over_delivery_counts"])))
            for n_deliveries in inning["over_delivery_counts"]:
                f.write(struct.pack(">B", n_deliveries))

        for val in delivery_bits:
            f.write(val.to_bytes(3, "big"))

        n = len(wicket_bits)
        for i in range(0, n, 8):
            byte = 0
            for j in range(8):
                if i + j < n and wicket_bits[i + j]:
                    byte |= (1 << (7 - j))
            f.write(bytes([byte]))

        for w in wicket_table:
            f.write(w.to_bytes(2, "big"))


def decompress(in_path):
    with open(in_path, "rb") as f:
        data = f.read()

    offset = 0
    num_players, num_deliveries = struct.unpack_from(">HH", data, offset)
    offset += 4

    players = []
    for _ in range(num_players):
        end = data.index(b"\x00", offset)
        players.append(data[offset:end].decode())
        offset = end + 1

    num_teams = data[offset]
    offset += 1
    teams = []
    for _ in range(num_teams):
        end = data.index(b"\x00", offset)
        teams.append(data[offset:end].decode())
        offset = end + 1
    team_player_counts = list(data[offset:offset + num_teams])
    offset += num_teams

    num_innings = data[offset]
    offset += 1
    innings_layout = []
    for _ in range(num_innings):
        team_index = data[offset]
        offset += 1

        num_overs = data[offset]
        offset += 1

        over_delivery_counts = list(data[offset:offset + num_overs])
        offset += num_overs

        innings_layout.append(
            {
                "team_index": team_index,
                "over_delivery_counts": over_delivery_counts,
            }
        )

    deliveries = []
    for _ in range(num_deliveries):
        val = int.from_bytes(data[offset:offset + 3], "big")
        offset += 3

        batter_runs = (val >> 2) & 0x7
        extras = (val >> 1) & 0x1
        deliveries.append(
            {
                "batter": players[(val >> 15) & 0x1F],
                "bowler": players[(val >> 10) & 0x1F],
                "non_striker": players[(val >> 5) & 0x1F],
                "runs": {
                    "batter": batter_runs,
                    "extras": extras,
                    "total": batter_runs + extras,
                },
                "has_wicket": val & 0x1,
            }
        )

    bitfield_bytes = (num_deliveries + 7) // 8
    wicket_bits = []
    for i in range(bitfield_bytes):
        byte = data[offset + i]
        for j in range(8):
            wicket_bits.append((byte >> (7 - j)) & 1)
    offset += bitfield_bytes

    wicket_table = []
    while offset + 2 <= len(data):
        val = int.from_bytes(data[offset:offset + 2], "big")
        offset += 2
        wicket_table.append(
            {
                "player_out": players[(val >> 6) & 0x1F],
                "fielder": players[(val >> 1) & 0x1F],
                "kind": "caught" if val & 1 else "bowled",
            }
        )

    for i, d in enumerate(deliveries):
        if wicket_bits[i]:
            idx = sum(wicket_bits[:i])
            w = wicket_table[idx]
            d["wickets"] = [{"player_out": w["player_out"], "kind": w["kind"]}]
            if w["kind"] == "caught":
                d["wickets"][0]["fielders"] = [{"name": w["fielder"]}]
        del d["has_wicket"]

    innings = []
    delivery_cursor = 0
    for inning in innings_layout:
        overs = []
        for over_no, count in enumerate(inning["over_delivery_counts"]):
            over_deliveries = deliveries[delivery_cursor:delivery_cursor + count]
            overs.append({"over": over_no, "deliveries": over_deliveries})
            delivery_cursor += count
        innings.append({"team": teams[inning["team_index"]], "overs": overs})

    players_map = {}
    player_cursor = 0
    for team, count in zip(teams, team_player_counts):
        players_map[team] = players[player_cursor:player_cursor + count]
        player_cursor += count

    return {
        "info": {
            "teams": teams,
            "players": players_map,
        },
        "innings": innings,
    }

if sys.argv[1] == "compress":
    compress(sys.argv[2], sys.argv[3])
elif sys.argv[1] == "decompress":
    result = decompress(sys.argv[2])
    print(json.dumps(result, indent=4))
