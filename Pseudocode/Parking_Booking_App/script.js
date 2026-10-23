const $=s=>document.querySelector(s);
const APP="ParkingBookingApp";
let mode="login",selectedSlot=null,selectedJob="";
const features=[];
function setMode(m){mode=m;document.querySelectorAll("[data-mode]").forEach(b=>b.classList.toggle("active",b.dataset.mode===m));$("#authTitle").textContent=m==="login"?"Welcome back":"Create your account";$("#submitBtn").textContent=m==="login"?"Login":"Register";$("#nameWrap").classList.toggle("hidden",m==="login");$("#name").required=m==="register";$("#authMsg").textContent="";}
document.querySelectorAll("[data-mode]").forEach(b=>b.addEventListener("click",()=>setMode(b.dataset.mode)));
function getUsers(){return JSON.parse(localStorage.getItem(APP+"_users")||"{}");}
$("#authForm").addEventListener("submit",e=>{e.preventDefault();const email=$("#email").value.trim().toLowerCase(),password=$("#password").value;let users=getUsers();if(mode==="register"){if(users[email]){$("#authMsg").textContent="This email is already registered.";return;}users[email]={name:$("#name").value.trim(),password};localStorage.setItem(APP+"_users",JSON.stringify(users));$("#authMsg").textContent="Registration successful. Please log in.";setMode("login");return;}if(!users[email]||users[email].password!==password){$("#authMsg").textContent="Account not found. Register first or check your details.";return;}sessionStorage.setItem(APP+"_current",email);showApp(users[email].name||email.split("@")[0]);});
function showApp(name){$("#auth").classList.add("hidden");$("#dashboard").classList.remove("hidden");$("#logoutBtn").classList.remove("hidden");$("#userName").textContent=name;renderSlots();}
function logout(){sessionStorage.removeItem(APP+"_current");$("#dashboard").classList.add("hidden");$("#auth").classList.remove("hidden");$("#logoutBtn").classList.add("hidden");$("#authForm").reset();setMode("login");selectedSlot=null;}
$("#logoutBtn").addEventListener("click",logout);

function getBooked(){return JSON.parse(localStorage.getItem("parkBookedSlots")||"[]");}
function renderSlots(){const booked=getBooked();$("#slots").innerHTML="";for(let i=1;i<=8;i++){const id="A"+String(i).padStart(2,"0"),taken=booked.includes(id),b=document.createElement("button");b.className="slot"+(taken?" booked":"")+(selectedSlot===id?" selected":"");b.disabled=taken;b.innerHTML=`<strong>${id}</strong><br>${taken?"🚗 Booked":"🅿️ Free"}`;b.addEventListener("click",()=>{selectedSlot=id;$("#bookBtn").disabled=false;$("#bookingMsg").textContent=`Selected ${id}. Press Book selected slot to confirm.`;renderSlots();});$("#slots").append(b);}$("#freeCount").textContent=8-booked.length;}
$("#bookBtn").addEventListener("click",()=>{if(!selectedSlot)return;let booked=getBooked();if(booked.includes(selectedSlot))return;booked.push(selectedSlot);localStorage.setItem("parkBookedSlots",JSON.stringify(booked));$("#bookingMsg").textContent=`Booking confirmed for slot ${selectedSlot}.`;selectedSlot=null;$("#bookBtn").disabled=true;renderSlots();});
$("#resetBtn").addEventListener("click",()=>{if(confirm("Reset demo parking bookings?")){localStorage.removeItem("parkBookedSlots");selectedSlot=null;$("#bookBtn").disabled=true;$("#bookingMsg").textContent="Demo parking data reset.";renderSlots();}});

const current=sessionStorage.getItem(APP+"_current");if(current){const users=getUsers();if(users[current])showApp(users[current].name||current.split("@")[0]);}
