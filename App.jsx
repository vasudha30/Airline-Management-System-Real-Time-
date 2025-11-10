import React, {useEffect, useState, useRef} from "react";

export default function App(){
  const [events, setEvents] = useState([]);
  const [seats, setSeats] = useState([]);
  const wsRef = useRef(null);
  const flightId = 1;

  useEffect(()=>{
    fetch(`/flights/${flightId}/seats`).then(r=>r.json()).then(setSeats);
    const ws = new WebSocket((location.protocol==='https:'?'wss://':'ws://') + location.host + '/ws');
    ws.onopen = ()=>console.log("ws open");
    ws.onmessage = (evt)=>{
      try {
        const d = JSON.parse(evt.data);
        setEvents(prev=>[d,...prev].slice(0,50));
        // reload seats when seat events occur
        if (d.type && d.type.startsWith('seat')) {
          fetch(`/flights/${flightId}/seats`).then(r=>r.json()).then(setSeats);
        }
      } catch(e){
        // ignore non-json messages
      }
    };
    wsRef.current = ws;
    return ()=> ws.close();
  },[]);

  return (
    <div style={{padding:20}}>
      <h1>AMS Staff Dashboard — Flight F100</h1>
      <div style={{display:'flex', gap:20}}>
        <div style={{flex:1}}>
          <h3>Seats</h3>
          <div style={{display:'flex', flexWrap:'wrap', gap:8}}>
            {seats.map(s=>(
              <div key={s.seat_code} style={{width:80,padding:8,border:'1px solid #333', textAlign:'center'}}>
                <div style={{fontWeight:600}}>{s.seat_code}</div>
                <div style={{fontSize:12,color:'#666'}}>{s.seat_class}</div>
              </div>
            ))}
          </div>
        </div>
        <div style={{width:420}}>
          <h3>Live events</h3>
          <div style={{height:500,overflow:'auto',border:'1px solid #ddd',padding:8}}>
            {events.map((e,i)=>(
              <div key={i} style={{padding:6,borderBottom:'1px solid #eee'}}>
                <pre style={{margin:0,whiteSpace:'pre-wrap'}}>{JSON.stringify(e)}</pre>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
