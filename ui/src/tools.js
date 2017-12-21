import axios from 'axios';

export const timestampToDatetime = (timestamp) => {
    var date = new Date(timestamp*1000);
    var formattedTime = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    return formattedTime;
}

export const axiosInstance = axios.create({
  baseURL: 'http://localhost:7001'
});

axios.defaults.baseURL = 'http://localhost:7001';