import React, { Component } from 'react';
import {MCardStats} from '../components/card.js';
import axios from 'axios';
import LinearProgress from 'material-ui/LinearProgress';

class Power extends Component {
  constructor(props) {
    super(props);
    this.state = {
      'status': 'Loading...'
    }
    this.props.socket.on('power_status', (socket) => {
      this.update();
    });
  }

  componentWillMount() {
    this.update();
  }

  update() {
    axios.get("/status_power").then((response) => {
      let data = response.data;
      this.setState((state) => {
        state['status'] = data.status;
        return state;
      });
    });
  }

  render() {
    return (
      <div className="col-lg-6 col-md-6 col-sm-6">
        <div className="card card-stats">
          <div className="card-header" data-background-color="green">
            <i className="material-icons">whatshot</i>
          </div>
          <div className="card-content">
            <p className="category">Power Status</p>
            <h3 className="title">{this.state.status}</h3>
          </div>
          <div className="card-footer">
            <div className="stats">
              <i className="material-icons">local_offer</i> Updated now!
            </div>
          </div>
        </div>
      </div>
    );
  }
}

export default Power;